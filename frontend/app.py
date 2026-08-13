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
    .stApp {
        background:
            radial-gradient(1100px 550px at 12% -8%, rgba(79,172,254,.16), transparent 60%),
            radial-gradient(900px 480px at 92% 0%, rgba(0,242,254,.10), transparent 55%),
            linear-gradient(160deg, #0b1220 0%, #0d1526 55%, #101a30 100%);
    }
    .block-container { max-width: 1280px; padding-top: 1.4rem; }
    .hero { margin-bottom: .9rem; }
    .hero-title {
        font-size: 2.4rem; font-weight: 800; letter-spacing: -.5px; line-height: 1.1;
        background: linear-gradient(92deg, #f5f9ff 10%, #7fd4ff 55%, #00f2fe 90%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text; margin: 0;
    }
    .hero-sub { color: #93a4c0; font-size: 1.0rem; margin-top: .35rem; }
    .chip {
        display: inline-block; padding: .18rem .7rem; border-radius: 999px;
        font-size: .78rem; font-weight: 600; letter-spacing: .2px;
        border: 1px solid rgba(255,255,255,.14); background: rgba(255,255,255,.05);
        color: #cfe0f5; margin: .15rem .4rem .15rem 0; white-space: nowrap;
    }
    .chip-ok { color: #8ef0c1; border-color: rgba(46,204,113,.45); background: rgba(46,204,113,.10); }
    .chip-err { color: #ffb4b4; border-color: rgba(255,80,80,.45); background: rgba(255,80,80,.10); }
    .result-card {
        border: 1px solid rgba(255,255,255,.10); border-radius: 16px;
        background: linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.02));
        padding: .85rem 1rem .7rem; margin-bottom: .8rem;
        box-shadow: 0 10px 30px rgba(0,0,0,.25);
    }
    .result-top { display: flex; align-items: center; gap: .65rem; margin-bottom: .4rem; }
    .rank-badge {
        min-width: 2.1rem; height: 2.1rem; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: .95rem; color: #0b1220;
        background: linear-gradient(135deg, #7fd4ff, #00a8ff);
        box-shadow: 0 4px 12px rgba(0,168,255,.35);
    }
    .rank-badge.rank1 { background: linear-gradient(135deg, #ffd76a, #ff9f1c); box-shadow: 0 4px 14px rgba(255,159,28,.45); }
    .result-name { font-size: 1.08rem; font-weight: 700; color: #eaf2ff; line-height: 1.25; }
    .result-id { color: #8fa3c2; font-size: .83rem; font-family: Consolas, "Cascadia Code", monospace; }
    .score-wrap { margin: .45rem 0 .1rem; }
    .score-label { display: flex; justify-content: space-between; font-size: .79rem; color: #9fb2d0; margin-bottom: .2rem; }
    .bar { height: .5rem; border-radius: 999px; background: rgba(255,255,255,.08); overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #00d2ff, #3a7bd5); }
    .meta-line { color: #8fa3c2; font-size: .81rem; margin-top: .3rem; }
    a.api-link { color: #00d2ff; text-decoration: none; font-weight: 600; }
    a.api-link:hover { text-decoration: underline; }
    .step-card {
        border: 1px solid rgba(255,255,255,.10); border-radius: 14px; padding: 1rem 1.1rem;
        background: rgba(255,255,255,.04); height: 100%;
    }
    .step-num {
        width: 1.7rem; height: 1.7rem; border-radius: 50%; display: flex; align-items: center;
        justify-content: center; font-weight: 700; font-size: .85rem; color: #0b1220;
        background: linear-gradient(135deg, #7fd4ff, #00a8ff); margin-bottom: .55rem;
    }
    .step-title { font-weight: 700; color: #eaf2ff; margin-bottom: .3rem; }
    .step-text { color: #93a4c0; font-size: .88rem; line-height: 1.45; }
    div[data-testid="stFileUploader"] section {
        border: 1.5px dashed rgba(0,210,255,.45) !important;
        border-radius: 14px;
    }
    div[data-testid="stFileUploader"] section:hover { border-color: #00d2ff !important; }
    .img-rounded { border-radius: 14px; border: 1px solid rgba(255,255,255,.12); }
    .result-img {
        width: 150px; height: 150px; object-fit: cover; flex-shrink: 0;
        border-radius: 12px; border: 1px solid rgba(255,255,255,.12);
        background: rgba(255,255,255,.04);
    }
</style>
"""

CSS_CLARO = """
<style>
    .stApp {
        background:
            radial-gradient(1000px 500px at 10% -5%, rgba(0,150,255,.10), transparent 55%),
            radial-gradient(800px 400px at 95% 0%, rgba(0,200,220,.08), transparent 50%),
            linear-gradient(160deg, #f4f8fd 0%, #e9f0f9 60%, #e2ecf8 100%);
    }
    [data-testid="stAppViewContainer"], [data-testid="stSidebar"],
    [data-testid="stMarkdownContainer"] { color: #1c2b3d; }
    .hero-title {
        background: linear-gradient(92deg, #0d2447 10%, #0068c8 55%, #0094b8 90%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .hero-sub { color: #44566f; }
    .chip { color: #33455e; border-color: rgba(20,40,70,.18); background: rgba(20,40,70,.05); }
    .chip-ok { color: #0b7a3d; border-color: rgba(34,153,84,.45); background: rgba(34,153,84,.10); }
    .chip-err { color: #b3261e; border-color: rgba(214,60,60,.45); background: rgba(214,60,60,.10); }
    .result-card {
        border: 1px solid rgba(20,40,70,.12);
        background: linear-gradient(180deg, #ffffff, #f6faff);
        box-shadow: 0 8px 24px rgba(30,60,100,.10);
    }
    .result-name { color: #0f2440; }
    .result-id { color: #5b6b84; }
    .score-label { color: #5b6b84; }
    .bar { background: rgba(20,40,70,.10); }
    .meta-line { color: #5b6b84; }
    a.api-link { color: #0068c8; }
    .step-card { border: 1px solid rgba(20,40,70,.12); background: #ffffff; }
    .step-title { color: #0f2440; }
    .step-text { color: #44566f; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #ffffff, #f0f5fb); }
    [data-testid="stSidebar"] hr { border-color: rgba(20,40,70,.15); }
    div[data-testid="stFileUploader"] section {
        border-color: rgba(0,104,200,.55) !important;
        background: rgba(255,255,255,.75);
    }
    div[data-testid="stFileUploader"] section span,
    div[data-testid="stFileUploader"] section button { color: #0f2440; }
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
        background: #ffffff !important;
    }
    div[data-baseweb="select"] span, div[data-baseweb="input"] input,
    div[data-baseweb="select"] input { color: #0f2440 !important; }
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
        border-color: rgba(20,40,70,.15) !important;
        background: rgba(255,255,255,.6) !important;
    }
    div[data-testid="stExpander"] summary { color: #0f2440 !important; }
    [data-testid="stCaptionContainer"] p { color: #5b6b84 !important; }
    .result-img { border-color: rgba(20,40,70,.14); background: #ffffff; }
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
    st.markdown(f"### {ICO['cpu']} Modelo de embeddings")
    modelo = st.selectbox(
        "Modelo",
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
    st.divider()
    with st.expander(f"{ICO['info']} Cómo funciona"):
        st.markdown(
            "1. **Subís** una imagen (JPG/JPEG/PNG).\n"
            "2. La **API** la prepara (Sala 2) y genera el embedding con CLIP.\n"
            "3. El **motor** recupera 30–100 candidatos y los reordena con "
            "reranking visual (color, estructura, patrón, marco, franjas).\n"
            "4. Se muestran las **5 más parecidas** con nombre, proveedor, "
            "URL y score de similitud.\n\n"
            "La interfaz solo consume la API; no genera embeddings ni busca localmente."
        )

info_health = st.session_state.get("health_info")
err_health = st.session_state.get("health_err")
chips = []
if info_health:
    chips.append(
        f'<span class="chip chip-ok">● API activa · '
        f'{esc(info_health.get("products", "?"))} productos</span>'
    )
    chips.append(f'<span class="chip">{ICO["shirt"]} {esc(info_health.get("embeddings", "?"))} embeddings</span>')
else:
    chips.append('<span class="chip chip-err">● API sin conexión</span>')
    if err_health:
        chips.append(f'<span class="chip chip-err">● {esc(err_health[:60])}</span>')

st.markdown(
    '<div class="hero">'
    '<h1 class="hero-title">Búsqueda visual de camisetas</h1>'
    '<div class="hero-sub">Subí una imagen y obtené las 5 camisetas más parecidas '
    'de la biblioteca.</div>'
    + "".join(chips) +
    "</div>",
    unsafe_allow_html=True,
)

archivo = st.file_uploader(
    "Subí una imagen de consulta (JPG, JPEG o PNG)",
    type=["jpg", "jpeg", "png"],
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
    c1, c2, c3 = st.columns(3)
    pasos = [
        ("1", "Subí tu imagen",
         "Puede ser la camiseta original, sin marco, recortada, con colores "
         "modificados o incluso una foto de persona usándola."),
        ("2", "La API la prepara y busca",
         "Sala 2 limpia la consulta y el motor recupera 30–100 candidatos, "
         "que luego reordena visualmente."),
        ("3", "Compará el Top 5",
         "Cada resultado muestra imagen, nombre, proveedor, URL y su score "
         "de similitud. Podés registrar la evaluación humana."),
    ]
    for col, (num, titulo, texto) in zip((c1, c2, c3), pasos):
        with col:
            st.markdown(
                f'<div class="step-card"><div class="step-num">{num}</div>'
                f'<div class="step-title">{titulo}</div>'
                f'<div class="step-text">{texto}</div></div>',
                unsafe_allow_html=True,
            )
    st.stop()

st.caption(f"Imagen: `{nombre_imagen}`")
clave_busqueda = hashlib.md5(datos_imagen + modelo.encode() + api_url.encode()).hexdigest()
if st.session_state.get("busqueda_clave") != clave_busqueda:
    with st.spinner("Buscando..."):
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
    st.markdown(f"#### {ICO['search']} Consulta")
    st.image(
        Image.open(io.BytesIO(datos_imagen)),
        use_container_width=True,
        caption="Imagen enviada",
    )

    b64_proc = data.get("imagen_procesada_b64")
    if b64_proc:
        try:
            st.image(
                Image.open(io.BytesIO(base64.b64decode(b64_proc))),
                use_container_width=True,
                caption="Preparada por la API (Sala 2)",
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

with col_r:
    st.markdown(f"#### {ICO['trophy']} Resultados")
    st.caption(
        f"Modo: `{esc(data.get('modo'))}` · "
        f"Modelo: `{esc(data.get('modelo'))}` · "
        f"Tiempo de respuesta: `{data.get('tiempo_segundos')} s`"
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

        meta = []
        if r.get("score_recuperacion") is not None:
            ini = r.get("posicion_inicial")
            fin = r.get("posicion_final")
            pos = f"#{ini} → #{fin}" if ini is not None and fin is not None else "—"
            meta.append(f"Recuperación: <code>{r['score_recuperacion']:.4f}</code> · Posición: <code>{pos}</code>")
        if r.get("modelo_utilizado"):
            meta.append(f"Modelo: <code>{esc(r['modelo_utilizado'])}</code>")

        link = ""
        if r.get("url"):
            link = (
                f'<div class="meta-line"><a class="api-link" '
                f'href="{esc(r["url"])}" target="_blank">{ICO["link"]}Abrir imagen original</a></div>'
            )

        st.markdown(
            '<div class="result-card">'
            '<div style="display:flex; gap:1rem; align-items:flex-start;">'
            f"{img_html}"
            '<div style="flex:1; min-width:0;">'
            '<div class="result-top">'
            f'<span class="rank-badge {"rank1" if rank == 1 else ""}">#{rank}</span>'
            '<div style="min-width:0;">'
            f'<div class="result-name">{esc(r.get("nombre"))}</div>'
            f'<div class="result-id">{esc(r.get("id"))} · Proveedor: {esc(r.get("proveedor"))}</div>'
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