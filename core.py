import os
import numpy as np
import rasterio
import pystac_client
import planetary_computer
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
from rasterio.transform import from_bounds as transform_from_bounds
from shapely.geometry import box, shape

# remove variáveis de ambiente conflitantes (ex: PROJ_LIB de uma instalação
# separada do PostgreSQL/PostGIS, da minha máquina) antes de importar rasterio, para evitar
# erro de leitura do banco de dados de sistemas de coordenadas (PROJ).
os.environ.pop("PROJ_LIB", None)
os.environ.pop("PROJ_DATA", None)

def buscar_cenas(bbox, data_inicio, data_fim, nuvem_max=20, colecao="landsat-c2-l2"):
    """Busca cenas no catálogo STAC e filtra por cobertura de nuvem no cliente.

    O filtro é aplicado aqui (em Python, lado cliente) e não via parâmetro `query` API,
    o servidor do Planetary Computer não garante suporte pleno à
    extensão QUERY do STAC, usando filtro do lado do servidor pode e retornava
    0 resultados mesmo havendo cenas disponíveis.
    """
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )
    search = catalog.search(
        collections=[colecao],
        bbox=bbox,
        datetime=f"{data_inicio}/{data_fim}",
    )
    todos_items = list(search.items())
    # print(f"[debug] total bruto antes do filtro: {len(todos_items)}") 

    items = [
        item for item in todos_items
        if item.properties.get("eo:cloud_cover", 100) < nuvem_max
    ]

    if not items:
        raise ValueError(
            f"{len(todos_items)} cena(s) encontrada(s) no período, mas nenhuma com "
            f"nuvem < {nuvem_max}%. Tente aumentar o limite de nuvem ou ampliar o intervalo de datas."
        )
    return items

def selecionar_melhor_cena(items, bbox):
    """Retorna a cena de menor nuvem entre as que cobrem o bbox inteiro."""
    area_interesse = box(*bbox)  # bbox em WGS84 (lon/lat)

    candidatas = [
        item for item in items
        if shape(item.geometry).contains(area_interesse)
    ]

    if not candidatas:
        raise ValueError(
            "Nenhuma cena cobre a área de interesse inteira — o bbox provavelmente "
            "atravessa a fronteira entre duas cenas Landsat. Tente uma área menor "
            "ou mais centralizada."
        )

    return min(candidatas, key=lambda item: item.properties["eo:cloud_cover"])

def ler_bandas(item, banda_a="red", banda_b="nir08"):
    """Lê duas bandas de uma cena e retorna os arrays + o perfil da banda_a."""
    with rasterio.open(item.assets[banda_a].href) as src_a:
        array_a = src_a.read(1).astype("float32")
        perfil = src_a.profile

    with rasterio.open(item.assets[banda_b].href) as src_b:
        array_b = src_b.read(1).astype("float32")

    return array_a, array_b, perfil

def calcular_indice(banda_nir, banda_red):
    """Calcula NDVI = (NIR - Red) / (NIR + Red)."""
    denominador = banda_nir + banda_red
    denominador[denominador == 0] = np.nan
    return (banda_nir - banda_red) / denominador

# Calcula NDWI = (gree - NIR) / (green + NIR)
def calcular_ndwi(banda_green, banda_nir):
    """Calcula NDWI = (Green - NIR) / (Green + NIR)."""
    denominador = banda_green + banda_nir
    denominador[denominador == 0] = np.nan
    return (banda_green - banda_nir) / denominador

def recortar(item, bbox, crs_destino, banda_a="red", banda_b="nir08"):
    bbox_utm = transform_bounds("EPSG:4326", crs_destino, *bbox)

    with rasterio.open(item.assets[banda_a].href) as src_a:
        print(f"[debug] transform banda A: {src_a.transform}")
        window_a = from_bounds(*bbox_utm, transform=src_a.transform)
        print(f"[debug] window A: col_off={window_a.col_off}, row_off={window_a.row_off}, width={window_a.width}, height={window_a.height}")
        array_a = src_a.read(1, window=window_a).astype("float32")

    with rasterio.open(item.assets[banda_b].href) as src_b:
        window_b = from_bounds(*bbox_utm, transform=src_b.transform)
        array_b = src_b.read(1, window=window_b).astype("float32")

    return array_a, array_b, bbox_utm

def exportar_geotiff(array, perfil_base, bbox_utm, caminho_saida):
    """Exporta um array 2D como GeoTIFF usando o perfil da cena original como base."""
    altura, largura = array.shape
    transform_clip = transform_from_bounds(*bbox_utm, largura, altura)

    perfil_saida = perfil_base.copy()
    perfil_saida.update({
        "driver": "GTiff",
        "height": altura,
        "width": largura,
        "transform": transform_clip,
        "dtype": "float32",
        "count": 1,
        "nodata": np.nan,
    })

    with rasterio.open(caminho_saida, "w", **perfil_saida) as dst:
        dst.write(array, 1)

    print(f"GeoTIFF salvo em: {caminho_saida}")

def gerar_preview(array, caminho_saida, titulo="NDVI", cmap="RdYlGn", vmin=None, vmax=None):
    """Gera um preview em PNG do índice calculado, com paleta de cores e barra de escala."""
    fig, ax = plt.subplots(figsize=(10, 8))

    array_mascarado = np.ma.masked_invalid(array)

    # se vmin/vmax não forem passados, usa o min/max real dos dados (equivalente ao "contínuo" do QGIS)
    if vmin is None:
        vmin = np.nanpercentile(array, 2)   # percentil 2% evita outliers puxando a escala
    if vmax is None:
        vmax = np.nanpercentile(array, 98)  # percentil 98% pelo mesmo motivo

    im = ax.imshow(array_mascarado, cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_title(titulo, fontsize=14, fontweight="bold")
    ax.axis("off")

    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cbar.set_label(titulo)

    plt.tight_layout()
    plt.savefig(caminho_saida, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"Preview salvo em: {caminho_saida}")