# Processador Automático de Índices Espectrais (NDVI/NDWI)

Aplicação em Python que busca, processa e calcula índices espectrais (NDVI e NDWI) a partir de imagens de satélite Landsat, de forma totalmente automatizada, sem download manual de imagens.

**App funcionando:** [https://ddynedif7tmbqouw2chqyz.streamlit.app/](#) 

![Preview do resultado](https://github.com/gabrielvieirad/auto-geo-indices-espectrais/blob/main/preview.jpg) 

## O que o projeto faz

Dado uma área de interesse (coordenadas), um período e um limite de cobertura de nuvem, o programa:

1. Busca automaticamente cenas Landsat disponíveis no catálogo público (via API STAC)
2. Seleciona a cena com menor cobertura de nuvem que cobre a área inteira
3. Lê as bandas espectrais necessárias
4. Recorta a imagem pela área de interesse
5. Calcula o índice escolhido (NDVI ou NDWI)
6. Gera um GeoTIFF (para uso em QGIS/ArcGIS) e um preview em PNG com paleta de cores

Tudo isso sem precisar baixar imagens manualmente de portais como USGS EarthExplorer.

## Índices disponíveis

| Índice | Fórmula | O que mede |
|---|---|---|
| **NDVI** | (NIR − Red) / (NIR + Red) | Vigor da vegetação |
| **NDWI** | (Green − NIR) / (Green + NIR) | Presença de água |

## Como usar

### Interface web (Streamlit)

```bash
pip install -r requirements.txt
streamlit run interface.py
```

Abre no navegador. Informe as coordenadas da área (bbox), o período, o limite de nuvem e o índice desejado, e clique em **Processar**.

### Linha de comando (CLI)

```bash
python main.py --bbox -60.5 -3.5 -60.0 -3.0 --inicio 2024-06-01 --fim 2024-09-30 --indice ndvi --saida resultado.tif
```

Parâmetros disponíveis:

| Parâmetro | Descrição |
|---|---|
| `--bbox` | Área de interesse em WGS84: `LON_MIN LAT_MIN LON_MAX LAT_MAX` |
| `--inicio` / `--fim` | Período de busca (AAAA-MM-DD) |
| `--nuvem-max` | Cobertura máxima de nuvem em % (padrão: 20) |
| `--satelite` | Satélite de origem (por enquanto só `landsat`) |
| `--indice` | Índice a calcular: `ndvi` ou `ndwi` |
| `--saida` | Caminho do GeoTIFF de saída |

## Arquitetura

```
codigos/
├── main.py         # Interface via linha de comando (CLI)
├── interface.py     # Interface web (Streamlit)
├── core.py          # Lógica principal: busca, processamento e cálculo dos índices
├── requirements.txt
└── .gitignore
```

A lógica de negócio fica isolada em `core.py`, reutilizada tanto pela CLI quanto pela interface web, nenhuma duplicação de código entre os dois modos de uso.

## Fonte dos dados

As imagens são obtidas via [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/), um catálogo público STAC com acesso gratuito às coleções Landsat Coleção 2 (Nível 2, já com correção atmosférica aplicada).

## Tecnologias

- **Python**
- [`rasterio`](https://rasterio.readthedocs.io/) — leitura, processamento e exportação de dados raster
- [`pystac-client`](https://pystac-client.readthedocs.io/) — busca no catálogo STAC
- [`numpy`](https://numpy.org/) — cálculo dos índices espectrais
- [`matplotlib`](https://matplotlib.org/) — geração dos previews coloridos
- [`geopandas`](https://geopandas.org/) — leitura de shapefile/GeoJSON (modo CLI)
- [`streamlit`](https://streamlit.io/) — interface web

## Próximos passos

- Adicionar suporte a Sentinel-2
- Adicionar NDBI (índice de área construída)
- Série temporal de índices ao longo de múltiplos anos para uma mesma área

## Autor

Gabriel Vieira — https://www.linkedin.com/in/gabrielvieirad/
