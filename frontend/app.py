# -*- coding: utf-8 -*-
"""
app.py - Interfaz de búsqueda visual (cliente puro de la API)
----------------------------------------------------------------
Sube una imagen y la API de Sala 3 devuelve el Top 5 de camisetas
más parecidas. Esta interfaz NO genera embeddings ni busca localmente:
solo consume POST /search/image.

Requisito: tener la API levantada antes de correr esto.
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

Correr desde la raíz del proyecto:
    streamlit run frontend/app.py
"""

import base64
import csv
import hashlib
import html
import io
import json
import os

import requests
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

# Importar sistema de identificación por país/equipo
try:
    from prompts.country_identification import (
        PAISES_FUTBOL,
        identificar_pais_equipo,
        construir_prompt_identificacion,
    )
    PROMPTS_DISPONIBLES = True
except ImportError:
    PROMPTS_DISPONIBLES = False

API_URL_DEFAULT = "http://localhost:8000"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES_DIR = os.path.join(BASE_DIR, "data", "images_normalized")
CONSULTAS_DIR = os.path.join(BASE_DIR, "data", "consultas")
EVALUACION_CSV = os.path.join(BASE_DIR, "data", "evaluation.csv")
TEMA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".theme_pref.json")
CLASIFICACIONES = ["Muy similar", "Similar", "Poco similar", "No relacionado"]
EXT_IMAGEN = (".jpg", ".jpeg", ".png")


def cargar_tema():
    """Lee la preferencia de tema guardada (claro/oscuro)."""
    try:
        with open(TEMA_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("tema", "oscuro")
    except Exception:
        return "oscuro"


def guardar_tema(tema):
    """Guarda la preferencia de tema para mantenerla entre sesiones."""
    try:
        with open(TEMA_FILE, "w", encoding="utf-8") as f:
            json.dump({"tema": tema}, f)
    except Exception:
        pass


if "tema_claro" not in st.session_state:
    st.session_state["tema_claro"] = cargar_tema() == "claro"

st.set_page_config(
    page_title="Búsqueda visual de camisetas",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": None,
        "Report a bug": None,
        "About": "**Búsqueda visual RAG** · Prototipo de búsqueda visual de "
                 "camisetas deportivas (hackatón).\n\nInterfaz: Sala 2 · "
                 "API: Sala 3 · Embeddings: Sala 4 · Datos: Sala 1",
    },
)

CSS = """
<style>
    @keyframes cardIn {
        from { opacity: 0; transform: translateY(16px); }
        to   { opacity: 1; transform: none; }
    }

    .stApp {
        background:
            radial-gradient(1200px 620px at 14% -12%, rgba(56,132,255,.15), transparent 60%),
            radial-gradient(1000px 540px at 90% -6%, rgba(0,220,255,.10), transparent 55%),
            radial-gradient(1000px 640px at 50% 118%, rgba(122,84,255,.08), transparent 62%),
            linear-gradient(172deg, #05070d 0%, #070b16 55%, #0a0f1e 100%);
        font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent; }
    [data-testid="stToolbar"] { visibility: hidden; }
    .block-container { max-width: 1140px; padding-top: 2.6rem; padding-bottom: 4rem; }

    /* ---------- Hero ---------- */
    .eyebrow { display: flex; align-items: center; gap: .55rem; margin-bottom: 1.1rem; }
    .eyebrow-dot {
        width: .55rem; height: .55rem; border-radius: 50%;
        background: linear-gradient(135deg, #00f2fe, #3a7bd5);
        box-shadow: 0 0 12px rgba(0,210,255,.85);
        animation: pulse 2.6s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(0,210,255,.45); }
        50%      { box-shadow: 0 0 0 6px rgba(0,210,255,0); }
    }
    .eyebrow-text {
        text-transform: uppercase; letter-spacing: .3em; font-size: .7rem;
        font-weight: 700; color: #8fb4e8;
    }
    .hero-title {
        font-size: clamp(2.1rem, 4.8vw, 3.35rem); font-weight: 800;
        letter-spacing: -.02em; line-height: 1.08; margin: 0 0 1rem;
        background: linear-gradient(94deg, #ffffff 0%, #cfe8ff 45%, #7fd4ff 78%, #00f2fe 100%);
        -webkit-background-clip: text; background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-sub {
        color: #9aa9c4; font-size: clamp(.98rem, 1.4vw, 1.08rem); line-height: 1.6;
        max-width: 580px; margin: 0 0 1.2rem;
    }
    .hero-meta {
        display: flex; flex-wrap: wrap; align-items: center; gap: .5rem;
        color: #7c8bab; font-size: .83rem;
    }
    .dot { width: .5rem; height: .5rem; border-radius: 50%; display: inline-block; margin-right: .35rem; }
    .dot-ok { background: #34d399; box-shadow: 0 0 8px rgba(52,211,153,.7); }
    .dot-err { background: #f87171; box-shadow: 0 0 8px rgba(248,113,113,.7); }
    .hero-meta-err { color: #f8a8a8; font-size: .8rem; margin-top: .45rem; }

    /* ---------- Área de subida ---------- */
    .upload-title { font-size: 1.22rem; font-weight: 650; color: #eef4ff; margin: 2.1rem 0 .2rem; }
    .upload-hint { font-size: .83rem; color: #7c8bab; margin-bottom: .9rem; }
    div[data-testid="stFileUploader"] section {
        border: 1.5px dashed rgba(125,170,230,.38) !important;
        border-radius: 22px !important;
        background: linear-gradient(180deg, rgba(255,255,255,.045), rgba(255,255,255,.015)) !important;
        backdrop-filter: blur(12px);
        min-height: 250px;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        transition: border-color .25s ease, box-shadow .25s ease, background .25s ease;
    }
    div[data-testid="stFileUploader"] section:hover {
        border-color: rgba(0,210,255,.8) !important;
        box-shadow: 0 0 0 1px rgba(0,210,255,.15), 0 26px 80px rgba(0,140,255,.18);
        background: linear-gradient(180deg, rgba(0,210,255,.05), rgba(255,255,255,.02)) !important;
    }
    div[data-testid="stFileUploader"] section:not(:has(div[data-testid="stFileUploaderDropzoneInstructions"])) {
        min-height: 90px;
    }
    div[data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
    div[data-testid="stFileUploaderDropzone"] button:has(+ div[data-testid="stFileUploaderDropzoneInstructions"]) { display: none !important; }
    div[data-testid="stFileUploaderDropzone"] > div:not(:last-child) { display: none !important; }
    div[data-testid="stFileUploader"] section:has(div[data-testid="stFileUploaderDropzoneInstructions"])::before {
        content: "";
        display: block; width: 58px; height: 58px; margin: 0 auto 16px;
        background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%2300d2ff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>') center/contain no-repeat;
        opacity: .9;
    }
    div[data-testid="stFileUploader"] section:has(div[data-testid="stFileUploaderDropzoneInstructions"])::after {
        content: "Arrastra tu imagen aquí\\A o haz clic para elegir archivo";
        display: block; text-align: center; white-space: pre-line;
        color: #aebdd8; font-size: .95rem; line-height: 1.55;
    }

    /* ---------- Flujo mínimo ---------- */
    .flow {
        margin-top: 2.5rem; text-align: center;
        color: #7c8bab; font-size: .92rem; line-height: 1.9;
    }
    .flow .n { color: #00d2ff; font-weight: 700; margin-right: .3rem; }
    .flow .arrow { color: rgba(255,255,255,.25); margin: 0 .75rem; font-style: normal; }

    /* ---------- Secciones ---------- */
    .section-head {
        display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between;
        gap: .5rem; margin: .5rem 0 1rem;
    }
    .section-title {
        font-size: .78rem; font-weight: 700; letter-spacing: .16em;
        text-transform: uppercase; color: #8fb4e8;
    }
    .section-meta { color: #7c8bab; font-size: .8rem; }

    /* ---------- Imágenes y consulta ---------- */
    [data-testid="stImage"] {
        border: 1px solid rgba(255,255,255,.1); border-radius: 18px; overflow: hidden;
        background: rgba(255,255,255,.03);
        box-shadow: 0 18px 55px rgba(0,0,0,.35);
    }
    [data-testid="stImage"] img { border-radius: 18px; }
    [data-testid="stImage"] figcaption, [data-testid="stCaptionContainer"] p { color: #7c8bab !important; }
    .query-status {
        display: inline-flex; align-items: center; gap: .45rem;
        margin: .5rem 0 1.1rem; padding: .32rem .85rem; border-radius: 999px;
        border: 1px solid rgba(52,211,153,.35); background: rgba(52,211,153,.08);
        color: #8ef0c1; font-size: .82rem;
    }
    .query-status code { color: #c8f7dd; font-size: .8rem; }

    /* ---------- Resultados ---------- */
    .result-card {
        border: 1px solid rgba(255,255,255,.09); border-radius: 18px;
        background: linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.015));
        backdrop-filter: blur(8px);
        padding: .9rem 1rem .8rem; margin-bottom: .9rem;
        box-shadow: 0 14px 40px rgba(0,0,0,.28);
        animation: cardIn .5s ease both;
        transition: border-color .2s ease, transform .2s ease;
    }
    .result-card:hover { border-color: rgba(0,210,255,.35); transform: translateY(-1px); }
    .result-layout { display: flex; gap: 1rem; align-items: flex-start; }
    .result-top { display: flex; align-items: center; gap: .65rem; margin-bottom: .5rem; }
    .rank-badge {
        min-width: 2.15rem; height: 2.15rem; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: .95rem; color: #04121f;
        background: linear-gradient(135deg, #7fd4ff, #00a8ff);
        box-shadow: 0 4px 14px rgba(0,168,255,.35);
    }
    .rank-badge.rank1 {
        background: linear-gradient(135deg, #ffd76a, #ff9f1c);
        box-shadow: 0 4px 16px rgba(255,159,28,.45);
    }
    .result-name { font-size: 1.04rem; font-weight: 700; color: #eaf2ff; line-height: 1.3; }
    .result-id { color: #7c8bab; font-size: .8rem; font-family: Consolas, "Cascadia Code", monospace; }
    .score-wrap { margin: .5rem 0 .15rem; }
    .score-label { display: flex; justify-content: space-between; font-size: .78rem; color: #9fb2d0; margin-bottom: .25rem; }
    .bar { height: .45rem; border-radius: 999px; background: rgba(255,255,255,.08); overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #00d2ff, #3a7bd5); }
    .meta-line { color: #7c8bab; font-size: .8rem; margin-top: .35rem; }
    a.api-link { color: #00d2ff; text-decoration: none; font-weight: 600; }
    a.api-link:hover { text-decoration: underline; }
    .result-img {
        width: 150px; height: 150px; object-fit: cover; flex-shrink: 0;
        border-radius: 14px; border: 1px solid rgba(255,255,255,.12);
        background: rgba(255,255,255,.04);
    }

    /* ---------- Widgets ---------- */
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
        background: rgba(255,255,255,.05) !important;
        border-color: rgba(255,255,255,.12) !important;
    }
    div[data-testid="stBaseButton-primary"] button {
        background: linear-gradient(90deg, #00a8ff, #00d2ff) !important;
        color: #04121f !important; font-weight: 700;
        box-shadow: 0 8px 24px rgba(0,170,255,.25);
    }
    div[data-testid="stBaseButton-primary"] button:hover {
        box-shadow: 0 10px 32px rgba(0,190,255,.4);
    }
    div[data-testid="stBaseButton-secondary"] button {
        background: rgba(255,255,255,.06) !important;
        color: #dce8ff !important;
        border-color: rgba(255,255,255,.14) !important;
    }
    div[data-testid="stExpander"] {
        background: rgba(255,255,255,.03) !important;
        border-color: rgba(255,255,255,.08) !important;
        border-radius: 14px !important;
    }
    div[data-testid="stExpander"] summary { color: #cfe0f5 !important; }

    /* ---------- Sidebar ---------- */
    [data-testid="stSidebar"] {
        background: rgba(7,10,18,.66);
        border-right: 1px solid rgba(255,255,255,.06);
        backdrop-filter: blur(14px);
    }
    [data-testid="stSidebar"] h3 {
        font-size: .8rem; letter-spacing: .14em; text-transform: uppercase; color: #8fb4e8;
    }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.08); }
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        background: rgba(255,255,255,.03) !important;
        border-color: rgba(255,255,255,.08) !important;
    }

    @media (max-width: 640px) {
        .block-container { padding-top: 1.7rem; }
        div[data-testid="stFileUploader"] section { min-height: 195px; }
        .result-card { padding: .8rem; }
        .result-layout { flex-wrap: wrap; }
    }
</style>
"""

CSS_CLARO = """
<style>
    .stApp {
        background:
            radial-gradient(1200px 620px at 14% -12%, rgba(56,132,255,.13), transparent 60%),
            radial-gradient(1000px 540px at 90% -6%, rgba(0,200,220,.10), transparent 55%),
            radial-gradient(1000px 640px at 50% 118%, rgba(122,84,255,.07), transparent 62%),
            linear-gradient(172deg, #f5f9fd 0%, #ebf2fa 55%, #e7eef8 100%);
    }
    [data-testid="stAppViewContainer"], [data-testid="stSidebar"],
    [data-testid="stMarkdownContainer"] { color: #18293f; }
    .hero-title {
        background: linear-gradient(94deg, #0b1f3a 0%, #1a4a8f 45%, #0077cc 78%, #0094b8 100%);
        -webkit-background-clip: text; background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-sub { color: #4a5d78; }
    .hero-meta { color: #5b6b84; }
    .hero-meta-err { color: #b3261e; }
    .eyebrow-text { color: #3b6ea8; }
    .upload-title { color: #0f2440; }
    .upload-hint { color: #5b6b84; }
    div[data-testid="stFileUploader"] section {
        border-color: rgba(0,104,200,.4) !important;
        background: linear-gradient(180deg, #ffffff, #f2f8ff) !important;
    }
    div[data-testid="stFileUploader"] section:hover {
        border-color: rgba(0,130,220,.85) !important;
        box-shadow: 0 0 0 1px rgba(0,130,220,.12), 0 26px 70px rgba(0,120,220,.14);
        background: linear-gradient(180deg, #ffffff, #eaf4ff) !important;
    }
    div[data-testid="stFileUploader"] section:has(div[data-testid="stFileUploaderDropzoneInstructions"])::before {
        background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%230077cc" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>') center/contain no-repeat;
    }
    div[data-testid="stFileUploader"] section:has(div[data-testid="stFileUploaderDropzoneInstructions"])::after {
        color: #44566f;
    }
    .flow { color: #5b6b84; }
    .flow .n { color: #0077cc; }
    .flow .arrow { color: rgba(20,40,70,.3); }
    .section-title { color: #2c5f9e; }
    .section-meta { color: #5b6b84; }
    [data-testid="stImage"] {
        border-color: rgba(20,40,70,.1); background: #ffffff;
        box-shadow: 0 14px 40px rgba(30,60,100,.12);
    }
    [data-testid="stImage"] figcaption, [data-testid="stCaptionContainer"] p { color: #5b6b84 !important; }
    .query-status {
        border-color: rgba(34,153,84,.4); background: rgba(34,153,84,.09); color: #0b7a3d;
    }
    .query-status code { color: #0b7a3d; }
    .result-card {
        border-color: rgba(20,40,70,.1);
        background: linear-gradient(180deg, #ffffff, #f6faff);
        box-shadow: 0 12px 34px rgba(30,60,100,.10);
    }
    .result-card:hover { border-color: rgba(0,120,220,.35); }
    .result-name { color: #0f2440; }
    .result-id { color: #5b6b84; }
    .score-label { color: #5b6b84; }
    .bar { background: rgba(20,40,70,.1); }
    .meta-line { color: #5b6b84; }
    a.api-link { color: #0068c8; }
    .result-img { border-color: rgba(20,40,70,.14); background: #ffffff; }
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
        background: #ffffff !important;
        border-color: rgba(20,40,70,.15) !important;
    }
    div[data-testid="stBaseButton-primary"] button {
        background: linear-gradient(90deg, #0077cc, #0094b8) !important;
        color: #ffffff !important;
    }
    div[data-testid="stBaseButton-secondary"] button {
        background: #ffffff !important;
        color: #0f2440 !important;
        border-color: rgba(20,40,70,.18) !important;
    }
    div[data-testid="stExpander"] {
        background: rgba(255,255,255,.55) !important;
        border-color: rgba(20,40,70,.12) !important;
    }
    div[data-testid="stExpander"] summary { color: #0f2440 !important; }
    [data-testid="stSidebar"] {
        background: rgba(255,255,255,.72);
        border-right: 1px solid rgba(20,40,70,.08);
    }
    [data-testid="stSidebar"] h3 { color: #2c5f9e; }
    [data-testid="stSidebar"] hr { border-color: rgba(20,40,70,.1); }
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        background: rgba(255,255,255,.6) !important;
        border-color: rgba(20,40,70,.12) !important;
    }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)
if st.session_state["tema_claro"]:
    st.markdown(CSS_CLARO, unsafe_allow_html=True)


ICO = {
    "gear": "⚙️",
    "zap": "⚡",
    "cpu": "🧠",
    "info": "ℹ️",
    "sun": "🌞",
    "target": "🎯",
    "search": "🔍",
    "trophy": "🏆",
    "wrench": "🛠️",
    "link": "🔗",
    "edit": "✏️",
    "shirt": "👕",
    "printer": "🖨️",
    "download": "⬇️",
}


def html_imprimir(b64, nombre_archivo, tema_claro):
    """Botón Imprimir: la imagen vive oculta dentro del iframe y solo se
    muestra en el medio de impresión. window.print() imprime el iframe
    (el sandbox de componentes permite modales)."""
    if tema_claro:
        bg, color, borde = "#ffffff", "#0f2440", "rgba(20,40,70,.16)"
        hover = "rgba(0,104,200,.08)"
    else:
        bg, color, borde = "rgba(255,255,255,.07)", "#cfe0f5", "rgba(255,255,255,.18)"
        hover = "rgba(0,210,255,.12)"
    return f"""
<style>
    html, body {{ margin: 0; padding: 0; background: transparent; }}
    button {{
        width: 100%; display: inline-flex; align-items: center; justify-content: center;
        padding: 6px 10px; border-radius: 9px; border: 1px solid {borde};
        background: {bg}; color: {color}; font-size: 13px; font-weight: 600;
        cursor: pointer; font-family: inherit; transition: background .15s;
    }}
    button:hover {{ background: {hover}; border-color: #00a8ff; }}
    .print-area {{ display: none; }}
    @media print {{
        body {{ background: #ffffff !important; }}
        button {{ display: none !important; }}
        .print-area {{
            display: flex !important; align-items: center; justify-content: center;
            min-height: 100vh; margin: 0;
        }}
        .print-area img {{ max-width: 100%; max-height: 100vh; object-fit: contain; }}
    }}
</style>
<div class="print-area"><img src="data:image/jpeg;base64,{b64}"/></div>
<button onclick="imprimir()">{ICO['printer']} Imprimir</button>
<script>
    const img = document.querySelector('.print-area img');
    function imprimir() {{
        if (!img.complete) {{
            img.onload = function () {{ window.print(); }};
        }} else {{
            window.print();
        }}
    }}
</script>
"""



def verificar_health(api_url):
    """Consulta GET /health y devuelve (info, error)."""
    try:
        resp = requests.get(f"{api_url.rstrip('/')}/health", timeout=6)
    except requests.exceptions.RequestException as exc:
        return None, str(exc)
    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code}: {resp.text[:200]}"
    return resp.json(), None


def buscar(datos, nombre, tipo, api_url, modelo):
    """Envía la imagen a la API y devuelve (datos, error)."""
    try:
        resp = requests.post(
            f"{api_url.rstrip('/')}/search/image",
            files={"file": (nombre, datos, tipo)},
            data={"modo": "auto", "modelo": modelo},
            timeout=180,
        )
    except requests.exceptions.ConnectionError:
        return None, "No se pudo conectar a la API. Ejecutá: uvicorn api.main:app --port 8000"
    except requests.exceptions.Timeout:
        return None, "La API tardó demasiado. Reintentá."
    if resp.status_code != 200:
        try:
            detalle = resp.json().get("error", resp.text[:300])
        except Exception:
            detalle = resp.text[:300]
        return None, f"Error de la API ({resp.status_code}): {detalle}"
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


def imagen_a_b64(ruta, alto=200):
    """Convierte una imagen local en data-URI base64 para mostrarla en HTML."""
    try:
        with Image.open(ruta) as im:
            im.thumbnail((alto * 2, alto * 2))
            buf = io.BytesIO()
            im.convert("RGB").save(buf, "JPEG", quality=82)
            return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None


def guardar_evaluacion(consulta, resultado_id, posicion, score, clasificacion, observacion):
    """Agrega una fila a data/evaluation.csv (consulta, resultado_id, posicion,
    score, clasificacion_humana, observacion)."""
    os.makedirs(os.path.dirname(EVALUACION_CSV), exist_ok=True)
    nuevo = not os.path.exists(EVALUACION_CSV)
    with open(EVALUACION_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if nuevo:
            writer.writerow([
                "consulta", "resultado_id", "posicion", "score",
                "clasificacion_humana", "observacion",
            ])
        writer.writerow([consulta, resultado_id, posicion, score, clasificacion, observacion])


def esc(texto):
    return html.escape(str(texto if texto is not None else ""))


def obtener_score(r):
    score = r.get("score_reranking")
    if score is None:
        score = r.get("score")
    try:
        return float(score or 0.0)
    except (TypeError, ValueError):
        return 0.0


def listar_consultas():
    if not os.path.isdir(CONSULTAS_DIR):
        return []
    return sorted(
        os.path.join(CONSULTAS_DIR, f)
        for f in os.listdir(CONSULTAS_DIR)
        if f.lower().endswith(EXT_IMAGEN)
    )


if "health_info" not in st.session_state:
    info, err = verificar_health(API_URL_DEFAULT)
    st.session_state["health_info"] = info
    st.session_state["health_err"] = err

with st.sidebar:
    tema_claro = st.toggle(
        "Tema claro",
        value=st.session_state["tema_claro"],
        help="Tema oscuro por defecto. La elección se recuerda entre sesiones.",
    )
    if tema_claro != st.session_state["tema_claro"]:
        st.session_state["tema_claro"] = tema_claro
        guardar_tema("claro" if tema_claro else "oscuro")

    st.markdown(f"### {ICO['gear']} Configuración")
    api_url = st.text_input(
        "URL de la API",
        value=st.session_state.get("api_url", API_URL_DEFAULT),
    )
    st.session_state["api_url"] = api_url

    if st.button("Verificar conexión", use_container_width=True):
        info, err = verificar_health(api_url)
        if err:
            st.error(f"No hay conexión con la API: {err}")
            st.session_state["health_info"] = None
            st.session_state["health_err"] = err
        else:
            st.session_state["health_info"] = info
            st.session_state["health_err"] = None
            st.success(
                f"API OK · {info.get('products', '?')} productos · "
                f"{info.get('embeddings', '?')} embeddings"
            )
            if info.get("desfase_detectado"):
                st.warning("Desfase detectado entre IDs y embeddings")

    st.divider()

    # Motor de búsqueda - Solo Fusión (ocl CLIP/OpenCLIP)
    st.markdown(f"### {ICO['cpu']} Motor de búsqueda")
    st.markdown(
        '<div style="'
        'padding: 0.8rem 1rem; '
        'border-radius: 12px; '
        'border: 1px solid rgba(0,210,255,0.3); '
        'background: linear-gradient(135deg, rgba(0,210,255,0.08), rgba(58,123,213,0.05)); '
        'margin-bottom: 0.5rem;'
        '">'
        '<div style="font-weight: 700; color: #00d2ff; font-size: 0.95rem; margin-bottom: 0.3rem;">'
        '⚡ Fusión (CLIP + OpenCLIP + SigLIP)'
        '</div>'
        '<div style="font-size: 0.82rem; color: #9aa9c4; line-height: 1.5;">'
        'Motor robusto que combina 3 modelos de visión. '
        'Si un punto o franja tapa parte del diseño, los otros modelos '
        'mantienen al producto correcto.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Variable de modelo (siempre fusion)
    modelo = "fusion"

    st.divider()

    # Identificación por país/equipo
    if PROMPTS_DISPONIBLES:
        st.markdown(f"### {ICO['target']} Identificación por país/equipo")
        st.markdown(
            '<div style="'
            'padding: 0.7rem 0.9rem; '
            'border-radius: 10px; '
            'border: 1px solid rgba(52,211,153,0.25); '
            'background: rgba(52,211,153,0.05); '
            'font-size: 0.82rem; color: #8ef0c1; line-height: 1.5;'
            '">'
            'El sistema identifica el <b>país</b> y <b>equipo</b> de la camiseta '
            'por sus colores, patrón y elementos distintivos. '
            'Busca similitudes visuales dentro del mismo país/equipo.'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="font-size: 0.78rem; color: #7c8bab; margin-top: 0.5rem;">'
            '<b>Países soportados:</b> Argentina, Brasil, España, Alemania, '
            'Francia, Inglaterra, Italia, Uruguay, Portugal, Colombia, '
            'México, Países Bajos, Japón, Corea del Sur, Nigeria, Senegal'
            '</div>',
            unsafe_allow_html=True,
        )
    st.divider()

    with st.expander(f"{ICO['info']} Cómo funciona"):
        st.markdown(
            "1. **Subís** una imagen (JPG/JPEG/PNG).\n"
            "2. La **API** la prepara (Sala 2) y genera embeddings con "
            "Fusión (3 modelos: CLIP + OpenCLIP + SigLIP).\n"
            "3. El **motor** recupera 200 candidatos y los reordena con "
            "reranking visual (color, estructura, patrón, marco, franjas).\n"
            "4. El sistema **identifica** el país y equipo por colores y patrón.\n"
            "5. Se muestran las **5 más parecidas** con nombre, proveedor, "
            "URL, score de similitud y país/equipo detectado.\n\n"
            "La interfaz solo consume la API; no genera embeddings ni busca localmente."
        )

info_health = st.session_state.get("health_info")
err_health = st.session_state.get("health_err")


def fmt_num(v):
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return esc(v) if v is not None else "?"


meta_parts = []
if info_health:
    meta_parts.append(f'{fmt_num(info_health.get("products"))} productos')
    meta_parts.append(f'{fmt_num(info_health.get("embeddings"))} embeddings')
    estado = '<span class="dot dot-ok"></span>API activa'
else:
    estado = '<span class="dot dot-err"></span>API sin conexión'
meta_html = '<div class="hero-meta">' + " · ".join(meta_parts) + ((" · " + estado) if meta_parts else estado) + "</div>"
if err_health:
    meta_html += f'<div class="hero-meta-err">No se pudo verificar la API: {esc(err_health[:70])}</div>'

st.markdown(
    '<div class="hero">'
    '<div class="eyebrow"><span class="eyebrow-dot"></span>'
    '<span class="eyebrow-text">Búsqueda visual</span></div>'
    '<h1 class="hero-title">Encuentra camisetas visualmente similares</h1>'
    '<div class="hero-sub">Sube una imagen de una camiseta y el sistema la analiza '
    'para encontrar las más parecidas de la biblioteca.</div>'
    + meta_html +
    "</div>",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="upload-title">Sube una imagen de camiseta</div>'
    '<div class="upload-hint">JPG, JPEG o PNG · Máximo 200 MB por archivo</div>',
    unsafe_allow_html=True,
)

archivo = st.file_uploader(
    "Sube una imagen de camiseta",
    type=["jpg", "jpeg", "png"],
    label_visibility="collapsed",
)

datos_imagen = None
nombre_imagen = None
tipo_imagen = None

if archivo is not None:
    datos_imagen = archivo.getvalue()
    nombre_imagen = archivo.name
    tipo_imagen = archivo.type or "image/jpeg"
else:
    consultas = listar_consultas()
    if consultas:
        with st.expander(f"{ICO['target']} Probar con una imagen del dataset de consultas"):
            seleccion = st.selectbox(
                "Imagen de prueba",
                consultas,
                format_func=lambda p: os.path.basename(p),
            )
            if st.button("Usar esta imagen", type="primary", use_container_width=True):
                st.session_state["ejemplo"] = seleccion
    ejemplo = st.session_state.get("ejemplo")
    if ejemplo and os.path.exists(ejemplo):
        with open(ejemplo, "rb") as f:
            datos_imagen = f.read()
        nombre_imagen = os.path.basename(ejemplo)
        ext = os.path.splitext(nombre_imagen)[1].lower()
        tipo_imagen = "image/png" if ext == ".png" else "image/jpeg"

if datos_imagen is None:
    st.markdown(
        '<div class="flow">'
        '<span class="n">01</span> Sube tu imagen <span class="arrow">→</span>'
        '<span class="n">02</span> La analizamos <span class="arrow">→</span>'
        '<span class="n">03</span> Encuentra similares'
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

st.markdown(
    f'<div class="query-status"><span class="dot dot-ok"></span>Imagen lista: '
    f'<code>{esc(nombre_imagen)}</code></div>',
    unsafe_allow_html=True,
)
clave_busqueda = hashlib.md5(datos_imagen + modelo.encode() + api_url.encode()).hexdigest()
if st.session_state.get("busqueda_clave") != clave_busqueda:
    with st.spinner("Procesando imagen y buscando similares..."):
        data, err = buscar(datos_imagen, nombre_imagen, tipo_imagen, api_url, modelo)
    st.session_state["busqueda_clave"] = clave_busqueda
    st.session_state["busqueda_data"] = data
    st.session_state["busqueda_err"] = err
else:
    data = st.session_state["busqueda_data"]
    err = st.session_state["busqueda_err"]
if err:
    st.error(err)
    st.stop()

if isinstance(data, dict):
    resultados = data.get("resultados") or []
else:
    resultados = data or []
    data = {}

if not resultados:
    st.info("No se encontraron resultados.")
    st.stop()

col_q, col_r = st.columns([1, 2.1], gap="large")

with col_q:
    st.markdown(
        f'<div class="section-title">{ICO["search"]} Consulta</div>',
        unsafe_allow_html=True,
    )
    st.image(
        Image.open(io.BytesIO(datos_imagen)),
        use_container_width=True,
        caption="Imagen de consulta",
    )

    b64_proc = data.get("imagen_procesada_b64")
    if b64_proc:
        try:
            st.image(
                Image.open(io.BytesIO(base64.b64decode(b64_proc))),
                use_container_width=True,
                caption="Preparada por la API",
            )
        except Exception:
            pass

    prep = data.get("preprocesamiento") or {}
    if prep.get("ok"):
        with st.expander(f"{ICO['wrench']} Detalles del preprocesamiento"):
            st.markdown(
                f"**Backend:** `{esc(prep.get('backend'))}` · "
                f"**Tiempo:** `{prep.get('tiempo_segundos')} s`"
            )
            if prep.get("bbox"):
                st.markdown(f"**BBox:** `{esc(prep.get('bbox'))}`")
            if prep.get("recorte_pct") is not None:
                st.markdown(f"**Recorte:** `{prep.get('recorte_pct')}%`")
            pasos = prep.get("pasos") or []
            if pasos:
                st.markdown("**Pasos aplicados:**")
                for paso in pasos:
                    st.markdown(f"- {esc(paso)}")

    # --- Identificación por país/equipo ---
    if PROMPTS_DISPONIBLES:
        st.markdown(f'<div class="section-title" style="margin-top: 1.2rem;">{ICO["target"]} Identificación</div>', unsafe_allow_html=True)

        # Extraer colores y patrón de los resultados si están disponibles
        colores_detectados = []
        patron_detectado = ""

        # Intentar extraer info del primer resultado o del embedding
        if resultados:
            primer_resultado = resultados[0]
            # Buscar colores en los metadatos del resultado
            modelo_info = primer_resultado.get("modelo_utilizado", "")
            if "color" in modelo_info.lower():
                patron_detectado = "multicolor"

        # Usar la función de identificación si tenemos colores
        if colores_detectados:
            paises_coincidentes = identificar_pais_equipo(colores_detectados, patron_detectado)
        else:
            # Si no detectamos colores, mostrar info general
            paises_coincidentes = []

        # Mostrar panel de identificación
        if paises_coincidentes:
            mejor_pais = paises_coincidentes[0]
            st.markdown(
                f'<div style="'
                f'padding: 0.8rem 1rem; '
                f'border-radius: 12px; '
                f'border: 1px solid rgba(52,211,153,0.35); '
                f'background: rgba(52,211,153,0.08); '
                f'margin-bottom: 0.5rem;'
                f'">'
                f'<div style="font-weight: 700; color: #8ef0c1; font-size: 0.95rem; margin-bottom: 0.3rem;">'
                f'🌍 {esc(mejor_pais["pais"])} — {esc(mejor_pais["seleccion"])}'
                f'</div>'
                f'<div style="font-size: 0.82rem; color: #9aa9c4; line-height: 1.5;">'
                f'{esc(mejor_pais["descripcion"])}'
                f'</div>'
                f'<div style="font-size: 0.78rem; color: #7c8bab; margin-top: 0.3rem;">'
                f'Colores: {esc(", ".join(mejor_pais["colores"]))} · '
                f'Coincidencia: {esc(mejor_pais["coincidencia_colores"])} · '
                f'Score: {mejor_pais["score_coincidencia"]:.2f}'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Mostrar equipos asociados
            if mejor_pais.get("equipos_famosos"):
                with st.expander(f"📋 Equipos de {esc(mejor_pais['pais'])}"):
                    for equipo in mejor_pais["equipos_famosos"][:6]:
                        st.markdown(f"- {esc(equipo)}")
        else:
            # Panel genérico cuando no hay identificación
            st.markdown(
                '<div style="'
                'padding: 0.7rem 0.9rem; '
                'border-radius: 10px; '
                'border: 1px solid rgba(127,212,255,0.25); '
                'background: rgba(127,212,255,0.05); '
                'font-size: 0.82rem; color: #9aa9c4; line-height: 1.5;'
                '">'
                'Sube una imagen y el sistema identificará el '
                '<b>país</b>, <b>equipo</b>, <b>colores</b> y <b>patrón</b> '
                'de la camiseta automáticamente.'
                '</div>',
                unsafe_allow_html=True,
            )

with col_r:
    st.markdown(
        '<div class="section-head">'
        f'<div class="section-title">{ICO["trophy"]} Resultados</div>'
        f'<div class="section-meta">Top 5 · Modo {esc(data.get("modo"))} · '
        f'Modelo {esc(data.get("modelo"))} · {data.get("tiempo_segundos")} s</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    consulta_id = esc(data.get("query_id")) or nombre_imagen

    for rank, r in enumerate(resultados, start=1):
        score = obtener_score(r)
        pct = max(0.0, min(100.0, score * 100.0))
        local = ruta_local(r.get("imagen", ""), r.get("id", ""))
        b64 = imagen_a_b64(local) if local else None
        if b64:
            img_html = f'<img class="result-img" src="data:image/jpeg;base64,{b64}"/>'
        elif r.get("url"):
            img_html = f'<img class="result-img" src="{esc(r["url"])}"/>'
        else:
            img_html = '<div class="result-img"></div>'

        # --- Identificar país/equipo del resultado ---
        pais_tag = ""
        if PROMPTS_DISPONIBLES:
            nombre_producto = (r.get("nombre") or "").lower()
            id_producto = (r.get("id") or "").lower()
            texto_busqueda = f"{nombre_producto} {id_producto}"

            # Buscar coincidencias en la base de datos
            for pais_key, info in PAISES_FUTBOL.items():
                # Verificar si el nombre del producto contiene el país o equipo
                if (pais_key in texto_busqueda or
                    info["nombre_completo"].lower() in texto_busqueda or
                    info["seleccion"].lower() in texto_busqueda):
                    pais_tag = (
                        f'<div style="'
                        f'display: inline-block; '
                        f'padding: 0.2rem 0.6rem; '
                        f'border-radius: 6px; '
                        f'background: rgba(52,211,153,0.15); '
                        f'border: 1px solid rgba(52,211,153,0.3); '
                        f'color: #8ef0c1; '
                        f'font-size: 0.75rem; '
                        f'font-weight: 600; '
                        f'margin-bottom: 0.4rem;'
                        f'">'
                        f'🌍 {esc(info["nombre_completo"])} · {esc(info["seleccion"])}'
                        f'</div>'
                    )
                    break

            # Si no se encontró país específico, intentar por colores en el nombre
            if not pais_tag:
                for color in ["celeste", "azul", "rojo", "verde", "amarillo", "naranja", "blanco", "negro"]:
                    if color in texto_busqueda:
                        # Buscar países con ese color
                        paises_color = [p for p, info in PAISES_FUTBOL.items() if color in info["colores"]]
                        if paises_color:
                            mejor_pais = paises_color[0]
                            info_pais = PAISES_FUTBOL[mejor_pais]
                            pais_tag = (
                                f'<div style="'
                                f'display: inline-block; '
                                f'padding: 0.2rem 0.6rem; '
                                f'border-radius: 6px; '
                                f'background: rgba(127,212,255,0.12); '
                                f'border: 1px solid rgba(127,212,255,0.25); '
                                f'color: #9aa9c4; '
                                f'font-size: 0.75rem; '
                                f'margin-bottom: 0.4rem;'
                                f'">'
                                f'🎨 Posible: {esc(info_pais["nombre_completo"])}'
                                f'</div>'
                            )
                            break

        meta = []
        if r.get("score_recuperacion") is not None:
            ini = r.get("posicion_inicial")
            fin = r.get("posicion_final")
            pos = f"#{ini} → #{fin}" if ini is not None and fin is not None else "—"
            meta.append(f"Recuperación: <code>{r['score_recuperacion']:.4f}</code> · Posición: <code>{pos}</code>")
        if r.get("modelo_utilizado"):
            meta.append(f"Modelo: <code>⚡ Fusión</code>")

        link = ""
        if r.get("url"):
            link = (
                f'<div class="meta-line"><a class="api-link" '
                f'href="{esc(r["url"])}" target="_blank">{ICO["link"]}Abrir imagen original</a></div>'
            )

        st.markdown(
            f'<div class="result-card" style="animation-delay:{rank * 70}ms">'
            '<div class="result-layout">'
            f"{img_html}"
            '<div style="flex:1; min-width:0;">'
            '<div class="result-top">'
            f'<span class="rank-badge {"rank1" if rank == 1 else ""}">#{rank}</span>'
            '<div style="min-width:0;">'
            f'<div class="result-name">{esc(r.get("nombre"))}</div>'
            f'<div class="result-id">{esc(r.get("id"))} · Proveedor: {esc(r.get("proveedor"))}</div>'
            f'{pais_tag}'
            "</div></div>"
            '<div class="score-wrap">'
            '<div class="score-label"><span>Score de similitud</span>'
            f"<span>{score:.4f}</span></div>"
            f'<div class="bar"><div class="bar-fill" style="width:{pct:.1f}%"></div></div>'
            "</div>"
            + ("".join(f'<div class="meta-line">{m}</div>' for m in meta))
            + link
            + "</div></div></div>",
            unsafe_allow_html=True,
        )

        if b64:
            nombre_archivo = f"{r.get('id', 'resultado')}.jpg"
            bytes_imagen = None
            if local:
                with open(local, "rb") as f:
                    bytes_imagen = f.read()
            if bytes_imagen:
                c_d, c_p = st.columns(2)
                with c_d:
                    st.download_button(
                        f"{ICO['download']} Descargar imagen",
                        data=bytes_imagen,
                        file_name=nombre_archivo,
                        mime="image/jpeg",
                        use_container_width=True,
                    )
                with c_p:
                    components.html(
                        html_imprimir(b64, nombre_archivo, st.session_state["tema_claro"]),
                        height=44,
                        scrolling=False,
                    )
            else:
                components.html(
                    html_imprimir(b64, nombre_archivo, st.session_state["tema_claro"]),
                    height=44,
                    scrolling=False,
                )

        with st.expander(f"{ICO['edit']} Evaluar resultado #{rank}"):
            clasificacion = st.selectbox(
                "Clasificación humana",
                CLASIFICACIONES,
                key=f"clasif_{rank}",
            )
            observacion = st.text_input(
                "Observación (opcional)",
                key=f"obs_{rank}",
            )
            if st.button("Guardar evaluación", key=f"btn_{rank}", type="primary"):
                guardar_evaluacion(
                    consulta_id,
                    r.get("id"),
                    rank,
                    score,
                    clasificacion,
                    observacion,
                )
                st.success("Evaluación guardada en data/evaluation.csv")