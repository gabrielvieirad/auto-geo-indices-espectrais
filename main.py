import argparse
import geopandas as gpd

from datetime import datetime
from core import (
    buscar_cenas, 
    selecionar_melhor_cena,
    ler_bandas,
    recortar,
    calcular_indice,
    exportar_geotiff,
    gerar_preview,
    calcular_ndwi,
)

SATELITES = {
    "landsat": "landsat-c2-l2",
}

def validar_data(valor):
    try:
        datetime.strptime(valor, "%Y-%m-%d")
        return valor
    except ValueError:
        raise argparse.ArgumentTypeError(f"Data inválida: {valor}. Use o formato AAAA-MM-YYYY.")

def obter_bbox(args):
    """Retorna o bbox em WGS84, a partir de --bbox ou de um shapefile/geojson."""
    if args.bbox:
        return args.bbox

    if args.shapefile:
        gdf = gpd.read_file(args.shapefile)
        if gdf.crs is None:
            raise ValueError("O arquivo de área não tem CRS definido.")
        gdf = gdf.to_crs("EPSG:4326")  # normaliza pra WGS84, mesmo padrão do bbox manual
        minx, miny, maxx, maxy = gdf.total_bounds
        return [minx, miny, maxx, maxy]

    raise ValueError("Informe --bbox ou --shapefile para definir a área de interesse.")

def main():
    parser = argparse.ArgumentParser(
        description="Busca, processa e calcula índices espectrais a partir de imagens de satélite."
    )

    area = parser.add_mutually_exclusive_group(required=True)
    area.add_argument(
        "--bbox", nargs=4, type=float,
        metavar=("LON_MIN", "LAT_MIN", "LON_MAX", "LAT_MAX"),
        help="Área de interesse em WGS84, ex: --bbox -60.5 -3.5 -60.0 -3.0"
    )
    area.add_argument(
        "--shapefile", type=str,
        help="Caminho para um shapefile ou GeoJSON definindo a área de interesse"
    )

    parser.add_argument("--inicio", type=validar_data, required=True, help="Data inicial (AAAA-MM-DD)")
    parser.add_argument("--fim", type=validar_data, required=True, help="Data final (AAAA-MM-DD)")
    parser.add_argument("--nuvem-max", type=float, default=20, help="Cobertura máxima de nuvem em %% (padrão: 20)")
    parser.add_argument(
        "--satelite", choices=list(SATELITES.keys()), default="landsat",
        help="Satélite de origem (por enquanto só 'landsat' disponível)"
    )
    parser.add_argument(
        "--indice", choices=["ndvi","ndwi"], default="ndvi",
        help="Índice espectral a calcular (NDVI ou NDWI)"
    )
    parser.add_argument("--saida", default="resultado.tif", help="Caminho do GeoTIFF de saída")

    args = parser.parse_args()
    bbox = obter_bbox(args)
    colecao = SATELITES[args.satelite]

    print(f"Satélite: {args.satelite} | Área: {bbox}")
    print(f"Buscando cenas entre {args.inicio} e {args.fim}, nuvem < {args.nuvem_max}%...")

    items = buscar_cenas(bbox, args.inicio, args.fim, nuvem_max=args.nuvem_max, colecao=colecao)
    print(f"{len(items)} cena(s) encontrada(s).")

    melhor = selecionar_melhor_cena(items, bbox)
    print(f"Cena selecionada: {melhor.id} ({melhor.properties['eo:cloud_cover']:.2f}% de nuvem)")

    if args.indice == "ndvi":
        banda_a, banda_b = "red", "nir08"
    elif args.indice == "ndwi":
        banda_a, banda_b = "green", "nir08"

    _, _, perfil = ler_bandas(melhor, banda_a=banda_a, banda_b=banda_b)
    array_a_clip, array_b_clip, bbox_utm = recortar(melhor, bbox, perfil["crs"], banda_a=banda_a, banda_b=banda_b)

    if args.indice == "ndvi":
        resultado = calcular_indice(array_b_clip, array_a_clip)
    elif args.indice == "ndwi":
        resultado = calcular_ndwi(array_a_clip, array_b_clip)

    exportar_geotiff(resultado, perfil, bbox_utm, args.saida)

    caminho_png = args.saida.replace(".tif", "_preview.png")
    gerar_preview(resultado, caminho_png, titulo=args.indice.upper())

if __name__ == "__main__":
    main()
