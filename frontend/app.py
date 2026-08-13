# -*- coding: utf-8 -*-
"""
app.py - Interfaz simple de búsqueda visual
-------------------------------------------
Sube una imagen, la API de Sala 3 la procesa y muestra las 5 camisetas
más parecidas. Nada más.

Requisito: tener la API levantada antes de correr esto.
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

Correr desde la raíz del proyecto:
    streamlit run frontend/app.py
"""

import io
import os

import requests
import streamlit as st
from PIL import Image

API_URL = "http://localhost:8000"
IMAGES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "images_normalized",
)

st.set_page_config(page_title="Búsqueda visual de camisetas", layout="wide")

st.title("Búsqueda visual de camisetas")
st.caption("Subí una imagen y obtené las 5 más parecidas.")


def buscar(archivo, modelo):
    """Envía la imagen a la API y devuelve (datos, error)."""
    try:
        resp = requests.post(
            f"{API_URL}/search/image",
            files={"file": (archivo.name, archivo.getvalue(), archivo.type)},
            data={"modo": "auto", "modelo": modelo},
            timeout=120,
        )
    except requests.exceptions.ConnectionError:
        return None, "No se pudo conectar a la API. Ejecutá: uvicorn api.main:app --port 8000"
    except requests.exceptions.Timeout:
        return None, "La API tardó demasiado. Reintentá."
    if resp.status_code != 200:
        return None, f"Error de la API ({resp.status_code}): {resp.text[:300]}"
    return resp.json(), None


def ruta_local(nombre, id_producto=""):
    ruta = os.path.join(IMAGES_DIR, nombre)
    if os.path.exists(ruta):
        return ruta
    if id_producto:
        ruta = os.path.join(IMAGES_DIR, f"{id_producto}.jpg")
        if os.path.exists(ruta):
            return ruta
    return None


archivo = st.file_uploader("Elegí una imagen (JPG, JPEG o PNG)", type=["jpg", "jpeg", "png"])
if archivo is None:
    st.stop()

modelo = st.radio(
    "Modelo de embeddings",
    options=["fusion", "openclip", "clip"],
    index=0,
    format_func=lambda m: {
        "fusion": "Fusión (CLIP + OpenCLIP + SigLIP) — más robusto",
        "openclip": "OpenCLIP (laion/CLIP-ViT-B-32-laion2B-s34B-b79K)",
        "clip": "CLIP (openai/clip-vit-base-patch32)",
    }[m],
    help="La fusión combina 3 modelos: si un punto o franja tapa parte del "
         "diseño en la foto, los otros modelos mantienen al producto correcto.",
)

col_q, col_r = st.columns([1, 2])
with col_q:
    st.subheader("Consulta")
    st.image(Image.open(io.BytesIO(archivo.getvalue())), use_container_width=True)

with col_r:
    st.subheader("Resultados")
    with st.spinner("Buscando..."):
        data, err = buscar(archivo, modelo)
    if err:
        st.error(err)
        st.stop()

    resultados = data.get("resultados") or []
    if not resultados:
        st.info("No se encontraron resultados.")
        st.stop()

    st.caption(
        f"Modo: `{data.get('modo')}` · "
        f"Modelo: `{data.get('modelo')}` · "
        f"Tiempo de respuesta: `{data.get('tiempo_segundos')}s`"
    )

    for rank, r in enumerate(resultados, start=1):
        c1, c2 = st.columns([1, 2.2])
        with c1:
            local = ruta_local(r.get("imagen", ""), r.get("id", ""))
            st.image(local if local else r["url"], use_container_width=True)
        with c2:
            st.markdown(f"**#{rank} — {r['nombre']}**")
            st.markdown(f"`{r['id']}` · Proveedor: `{r['proveedor']}`")
            score = r.get("score_reranking")
            if score is None:
                score = r["score"]
            st.markdown(f"**Similitud:** `{score:.4f}`")
            if r.get("score_recuperacion") is not None:
                ini = r.get("posicion_inicial")
                fin = r.get("posicion_final")
                pos = f"`#{ini} → #{fin}`" if ini is not None and fin is not None else ""
                st.caption(
                    f"Recuperación: `{r['score_recuperacion']:.4f}` · "
                    f"Reranking: `{score:.4f}` · Posición {pos}"
                )
            if r.get("url"):
                st.markdown(f"[Abrir imagen original]({r['url']})")
        st.divider()
