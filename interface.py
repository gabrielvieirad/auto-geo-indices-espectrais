import streamlit as st
import numpy as np

from datetime import datetime as dt
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

st.set_page_config(
    page_title="Processador de Índices Espectrais",
    layout="wide"
)

st.title("Processador Automático de Imagens de Satélite")
st.markdown(
    "Busca, processa e calcula índices espectrais (NDVI) a partir de imagens Landsat, "
    "usando o catálogo público do Microsoft Planetary Computer."
)

col1, col2 = st.columns(2)
bbox = None

with col1:
    st.subheader("Área de interesse")
    st.write("Defina a área de interesse por coordenadas geográficas.")
    lon_min = st.number_input(
        "Longitude mínima",
        value=None,
        placeholder="-60.5000",
        format="%.4f"
    )

    lat_min = st.number_input("Latitude mínima",value=None,placeholder="-3.5000",format="%.4f")
    lon_max = st.number_input("Longitude máxima",value=None,placeholder="-60.0000",format="%.4f")
    lat_max = st.number_input("Latitude máxima",value=None,placeholder="-3.0000",format="%.4f")

    if all(v is not None for v in [lon_min, lat_min, lon_max, lat_max]):
        bbox = [
            lon_min,
            lat_min,
            lon_max,
            lat_max
        ]

with col2:

    st.subheader("Parâmetros de busca")
    data_inicio = st.date_input("Data inicial")
    data_fim = st.date_input("Data final")
    
    nuvem_max = st.slider("Cobertura máxima de nuvem (%)",0,100,20)
    indice = st.selectbox("Índice espectral",["NDVI", "NDWI"])

st.divider()

if st.button("Processar", type="primary"):
    if bbox is None:
        st.error("Preencha todas as coordenadas da área de interesse.")

    elif data_fim <= data_inicio:
        st.error("A data final precisa ser posterior à data inicial.")

    else:
        status = st.status("Processando...",expanded=True)

        try:
            status.write("Buscando cenas no catálogo Landsat...")
            
            satelite = "landsat"
            items = buscar_cenas(bbox,str(data_inicio),str(data_fim),nuvem_max=nuvem_max)

            status.write(f"{len(items)} cena(s) encontrada(s). "
                "Selecionando a de menor cobertura de nuvem..."
            )

            melhor = selecionar_melhor_cena(items,bbox)
            
            data_cena = dt.fromisoformat(melhor.properties["datetime"].replace("Z", "+00:00")).strftime("%Y%m%d")
            nome_base = f"{satelite}_{data_cena}_{indice}"

            nome_tif = f"{nome_base}.tif"
            nome_png = f"{nome_base}_preview.png"

            status.write(
                f"Cena selecionada: **{melhor.id}** "
                f"({melhor.properties['eo:cloud_cover']:.2f}% de nuvem)"
            )

            status.write("Lendo bandas e recortando pela área de interesse...")

            if indice == "NDVI":
                banda_a, banda_b = "red", "nir08"
            elif indice == "NDWI":
                banda_a, banda_b = "green", "nir08"

            status.write("Lendo bandas e recortando pela área de interesse...")
            _, _, perfil = ler_bandas(melhor, banda_a=banda_a, banda_b=banda_b)
            array_a_clip, array_b_clip, bbox_utm = recortar(melhor, bbox, perfil["crs"], banda_a=banda_a, banda_b=banda_b)

            status.write(f"Calculando {indice}...")
            if indice == "NDVI":
                resultado = calcular_indice(array_b_clip, array_a_clip)
            elif indice == "NDWI":
                resultado = calcular_ndwi(array_a_clip, array_b_clip)

            # --- debug  ---

            # print(f"[debug] bbox original: {bbox}")
            # print(f"[debug] bbox_utm: {bbox_utm}")
            # print(f"[debug] shape red_clip: {red_clip.shape}")
            # print(f"[debug] shape nir_clip: {nir_clip.shape}")
            # print(f"[debug] shape resultado: {resultado.shape}")
            # print(f"[debug] min/max resultado: "f"{np.nanmin(resultado)} / "f"{np.nanmax(resultado)}")

            # --- fim debug ---

            status.write("Exportando resultados...")

            exportar_geotiff(resultado, perfil, bbox_utm, nome_tif)
            
            cmap = "RdYlGn" if indice == "NDVI" else "GnBu"
            gerar_preview(resultado, nome_png, titulo=indice, cmap=cmap)
            
            status.update(label="Concluído!",state="complete")
            st.image("nome.png",caption=f"{indice} calculado para a área selecionada",width="stretch")

            col_a, col_b = st.columns(2)
            with col_a:
                with open(nome_tif, "rb") as f:
                    st.download_button("Baixar GeoTIFF",f,file_name=nome_tif)

            with col_b:
                with open(nome_png, "rb") as f:
                    st.download_button("Baixar preview (PNG)",f,file_name=nome_png)

        except ValueError as e:

            status.update(label="Erro",state="error")
            st.error(str(e))

        except Exception as e:
            status.update(label="Erro",tate="error")
            st.error(f"Erro inesperado: {e}")