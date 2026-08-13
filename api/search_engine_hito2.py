# -*- coding: utf-8 -*-
"""
search_engine_hito2.py
----------------------
SALA 3 - Hito 2: Motor mejorado y reranking del Top 5.

El Hito 1 (api/search_engine.py) devuelve los 5 candidatos más cercanos
según CLIP. El problema observado es que el Top 1 suele ser correcto, pero
el Top 2-5 a veces son matemáticamente cercanos en el espacio de CLIP y
visualmente irrelevantes para una persona (por ejemplo, mismos colores pero
diseño distinto, o diseño distinto con misma estructura).

Para solucionarlo, este módulo NO reemplaza el Hito 1: lo usa como capa
base y le agrega una capa de reranking visual. El pipeline es:

1) RECUPERACIÓN AMPLIA: pedimos más candidatos de los que vamos a devolver
   (p.ej. 30 en vez de 5). Así el reranking no se queda ciego: si el diseño
   correcto quedó en el puesto 12 del ranking de CLIP, todavía puede subir.

2) RERANKING VISUAL (múltiples criterios, pesos en constantes para probar):
   a) COLOR GLOBAL: histograma HSV de la imagen completa. El color es un
      atributo que CLIP promedia en todo el espacio de la imagen y puede
      "esconder"; la comparación directa de histogramas refuerza la
      similitud percibida por una persona.
   b) COLOR POR REGIONES (frente/espalda): el banco tiene una estructura
      consistente (frente a la izquierda, espalda a la derecha, ver
      data/informe_formatos.txt). Se divide cada imagen en dos mitades y se
      compara el histograma de cada mitad por separado. Así un diseño con el
      frente parecido pero espalda distinta no gana solo por el promedio.
   c) ESTRUCTURA / DISTRIBUCIÓN DEL PATRÓN: comparación en escala de grises
      a baja resolución (32x32). Captura la "forma" del diseño
      independiente del color: dos versiones recoloreadas del mismo diseño
      quedan cerca, mientras que un diseño distinto con los mismos colores
      se aleja.
   d) DESCRIPTORES AVANZADOS (api/descriptores_visuales.py): color
      dominante y gama cromática (k-means HSV + histograma grueso), patrón
      de diseño (energía de textura en grilla), estructura con/sin marco
      (banda perimetral uniforme) y elementos gráficos específicos
      (franjas/rayas horizontales y verticales + banda central). Cubren los
      atributos que una persona usa para filtrar "a simple vista".

3) SCORE PONDERADO: primero se NORMALIZA el score CLIP por consulta
   (min-max sobre los candidatos recuperados) para que quede en la misma
   escala [0,1] que los descriptores visuales; luego se combinan con pesos
   ajustables. Los pesos se calibran con las 50 consultas de la evaluación
   (scripts/generar_consultas_prueba.py + scripts/compare_hito1_hito2.py).

4) UMBRAL DINÁMICO: en vez de forzar siempre 5 resultados, descartamos los
   candidatos que quedan demasiado por debajo del mejor. Si no hay suficiente
   calidad, se devuelven menos resultados (prefiero pocos y buenos a 5 con
   "relleno").

Nota sobre las imágenes del catálogo: se leen con PIL (no con cv2.imread)
porque cv2.imread falla con rutas que contienen caracteres no-ASCII (p.ej.
la carpeta "Imágenes" del perfil de Windows), lo que dejaba score_color en 0.
"""

import json
import os

import cv2
import numpy as np
from PIL import Image

from api.search_engine import DATADIR, search_similar
from api.descriptores_visuales import (
    descriptores_de_bgr,
    similitudes_visuales,
)

# ── PESOS DEL SCORE FINAL (probar, no asumir) ────────────────────────────
# Score_final = Σ peso_atributo * score_atributo, con el score de embeddings
# normalizado a [0,1] por consulta para que las escalas sean comparables.
# Los pesos se normalizan para que sumen 1. El embedding manda (0.50): es la
# señal MÁS robusta a oclusiones (un punto/franja que tape parte del diseño
# corrompe los descriptores de píxeles, no el vector semántico del modelo).
PESO_EMBEDDING       = 0.50   # el embedding sigue mandando (robusto a oclusiones)
PESO_COLOR_GLOBAL    = 0.07   # paleta global percibida por una persona
PESO_COLOR_FRENTE    = 0.04   # región izquierda (frente en el banco)
PESO_COLOR_ESPALDA   = 0.04   # región derecha (espalda en el banco)
PESO_ESTRUCTURA      = 0.07   # distribución del patrón en grises (robusto al color)
PESO_COLOR_DOMINANTE = 0.08   # color dominante (k-means HSV)
PESO_GAMA            = 0.04   # gama cromática (histograma HSV grueso)
PESO_PATRON          = 0.06   # diseño/patrón (textura en grilla)
PESO_MARCO           = 0.06   # estructura con/sin marco
PESO_FRANJAS         = 0.04   # líneas/franjas/rayados (elementos gráficos)

_PESOS = {
    "embedding": PESO_EMBEDDING,
    "color_global": PESO_COLOR_GLOBAL,
    "color_frente": PESO_COLOR_FRENTE,
    "color_espalda": PESO_COLOR_ESPALDA,
    "estructura": PESO_ESTRUCTURA,
    "color_dominante": PESO_COLOR_DOMINANTE,
    "gama": PESO_GAMA,
    "patron": PESO_PATRON,
    "marco": PESO_MARCO,
    "franjas": PESO_FRANJAS,
}
_total_pesos = sum(_PESOS.values())
PESOS = {k: v / _total_pesos for k, v in _PESOS.items()}

# Margen de corte dinámico: se descartan candidatos cuyo score_final quede
# más de este valor por debajo del mejor resultado (escala [0,1] normalizada)
MARGEN_CORTE = 0.25

# Carpeta de imágenes del catálogo usada SIEMPRE para el reranking visual.
# Es la fuente única de búsqueda: data/images_normalized/ (banco limpio de
# Sala 1). Tanto el índice del Hito 2 (embeddings_clip/openclip/siglip) como
# los descriptores de color/estructura se calculan sobre ESTA misma carpeta,
# así que el score de embeddings y los descriptores visuales son coherentes.
CARPETA_IMAGENES = os.path.join(DATADIR, "images_normalized")

# Índices del Hito 2 (Sala 4): generados por scripts/generar_indices_comparativos.py
# sobre data/images_normalized/. Todos con la MISMA estructura: embeddings L2
# + ids.npy alineado posicionalmente con products.csv (se pueden fusionar).
#   - "clip"    : openai/clip-vit-base-patch32 (el estándar del proyecto)
#   - "openclip": laion/CLIP-ViT-B-32-laion2B-s34B-b79K (más robusto a
#                 franjas/dibujos centrales y variaciones de diseño)
#   - "siglip"  : google/siglip-base-patch16-224 (complementario)
INDICES_NORMALIZADOS = {
    "clip": os.path.join(DATADIR, "embeddings_clip.npy"),
    "openclip": os.path.join(DATADIR, "embeddings_openclip.npy"),
    "siglip": os.path.join(DATADIR, "embeddings_siglip.npy"),
}
INDICE_NORMALIZADO = INDICES_NORMALIZADOS["clip"]
IDS_NORMALIZADO = os.path.join(DATADIR, "ids.npy")

# Descriptores avanzados precomputados (scripts/precomputar_descriptores.py)
DESCRIPTORES_JSON = os.path.join(DATADIR, "descriptores.json")

# Resolución de la comparación estructural (baja = robusta a detalles)
TAM_ESTRUCTURA = 32

# Cache de descriptores: cada imagen real se lee y procesa una sola vez por
# proceso. Con un catálogo fijo de 1000 imágenes esto evita re-leer el
# archivo en cada consulta y acelera mucho la evaluación con 50 queries.
_cache_descriptores = {}

# Cache de índices normalizados (Sala 4): { modelo: (embeddings, ids, df, válido) }
_cache_indices = {}

# Descriptores avanzados precomputados: { id_catalogo: descriptores }
_cache_descripciones_pre = {}

# Descriptores avanzados calculados on-the-fly (solo si no hay precomputados)
_cache_avanzados_online = {}

# La carpeta de imágenes es SIEMPRE images_normalized (ver
# _carpeta_imagenes_activa), independientemente del índice usado, por lo que
# los descriptores visuales siempre se calculan sobre el banco limpio.


# ─────────────────────────────────────────────
# LECTURA Y DESCRIPTORES
# ─────────────────────────────────────────────

def _leer_bgr_desde_ruta(ruta):
    """
    Lee una imagen desde disco y la devuelve como arreglo BGR (formato de
    OpenCV). Usa PIL para tolerar rutas con caracteres no-ASCII, donde
    cv2.imread falla silenciosamente (devuelve None).
    """
    try:
        im = Image.open(ruta).convert("RGB")
    except Exception:
        return None
    return cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)


def _a_imagen_bgr(imagen):
    """
    Convierte la imagen de consulta a un arreglo BGR (formato que espera
    OpenCV). Acepta una ruta de archivo (str), un objeto PIL.Image (lo que
    recibe el endpoint) o un arreglo numpy ya en BGR. Devuelve None si no
    se puede obtener una imagen válida.
    """
    if imagen is None:
        return None

    # Ruta de archivo
    if isinstance(imagen, (str, os.PathLike)):
        return _leer_bgr_desde_ruta(str(imagen))

    # Objeto PIL.Image (como lo abre api/main.py)
    if hasattr(imagen, "convert"):
        try:
            arr = np.array(imagen.convert("RGB"))
        except Exception:
            return None
        # PIL entrega RGB, OpenCV trabaja en BGR: hay que reordenar canales
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

    # Arreglo numpy ya preparado
    if isinstance(imagen, np.ndarray):
        return imagen

    return None


def _histograma_hsv(bgr):
    """
    Calcula el histograma HSV normalizado de una imagen BGR.
    El espacio HSV separa el color (H/S) del brillo (V), por eso responde
    mejor que RGB a "la paleta de colores del diseño", que es lo que una
    persona percibe primero en una camiseta.
    """
    if bgr is None or bgr.size == 0:
        return None

    # Si llegó una imagen en escala de grises (1 canal), la repetimos a BGR
    if bgr.ndim == 2:
        bgr = cv2.cvtColor(bgr, cv2.COLOR_GRAY2BGR)

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    # 8 bins por canal: un balance entre granularidad y ruido. Si pusiéramos
    # 256 bins, dos fotos del mismo diseño con distinta iluminación darían
    # histogramas "distintos"; con pocos bins se captura la paleta global.
    histograma = cv2.calcHist(
        [hsv], [0, 1, 2], None,
        [8, 8, 8], [0, 180, 0, 256, 0, 256],
    )

    # Normalizar para que la comparación no dependa del tamaño/resolución
    cv2.normalize(histograma, histograma, 0, 1, cv2.NORM_MINMAX)
    return histograma


def _mitades_bgr(bgr):
    """Divide una imagen BGR en (izquierda, derecha) por la mitad del ancho."""
    if bgr is None or bgr.size == 0:
        return None, None
    w = bgr.shape[1]
    return bgr[:, : w // 2], bgr[:, w // 2 :]


def _estructura_gris(bgr):
    """
    Descriptor estructural: imagen en escala de grises redimensionada a
    TAM_ESTRUCTURA x TAM_ESTRUCTURA y normalizada a [0, 1]. Representa la
    distribución espacial del patrón independiente del color.
    """
    if bgr is None or bgr.size == 0:
        return None
    if bgr.ndim == 3:
        gris = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    else:
        gris = bgr
    gris = cv2.resize(gris, (TAM_ESTRUCTURA, TAM_ESTRUCTURA),
                      interpolation=cv2.INTER_AREA)
    return gris.astype(np.float32) / 255.0


def _correlacion_estructura(a, b):
    """
    Coeficiente de correlación de Pearson entre dos descriptores
    estructurales (1 = misma distribución del patrón). Si ambos son planos
    (sin patrón), se consideran iguales estructuralmente; si solo uno es
    plano, no hay información compartida y se devuelve 0.
    """
    if a is None or b is None:
        return 0.0
    fa = a.ravel()
    fb = b.ravel()
    std_a, std_b = fa.std(), fb.std()
    if std_a < 1e-6 and std_b < 1e-6:
        return 1.0
    if std_a < 1e-6 or std_b < 1e-6:
        return 0.0
    corr = float(np.corrcoef(fa, fb)[0, 1])
    return max(0.0, min(1.0, corr))


def _sim_color(a, b):
    """Similitud de histogramas HSV por correlación, recortada a [0, 1]."""
    if a is None or b is None:
        return 0.0
    sim = float(cv2.compareHist(a, b, cv2.HISTCMP_CORREL))
    return max(0.0, min(1.0, sim))


def _descriptores_de_archivo(nombre_archivo, id_catalogo=None):
    """
    Lee la imagen real de un candidato desde data/images_normalized/ y
    devuelve sus descriptores: (hist_global, hist_frente, hist_espalda,
    estructura) más los avanzados. Usa cache para no re-leer el archivo en
    cada query. Devuelve None si la imagen no existe o no se puede abrir.
    """
    clave = (CARPETA_IMAGENES, str(nombre_archivo), str(id_catalogo))
    if clave in _cache_descriptores:
        return _cache_descriptores[clave]

    ruta = _resolver_imagen(nombre_archivo, id_catalogo)
    bgr = _leer_bgr_desde_ruta(ruta) if ruta else None
    if bgr is None:
        _cache_descriptores[clave] = None
        return None

    izq, der = _mitades_bgr(bgr)
    desc = {
        "hist_global": _histograma_hsv(bgr),
        "hist_frente": _histograma_hsv(izq),
        "hist_espalda": _histograma_hsv(der),
        "estructura": _estructura_gris(bgr),
        "avanzados": descriptores_de_bgr(bgr),
    }
    _cache_descriptores[clave] = desc
    return desc


# ─────────────────────────────────────────────
# DESCRIPTORES AVANZADOS (precomputados u on-the-fly)
# ─────────────────────────────────────────────

def cargar_descriptores_precomputados():
    """
    Carga data/descriptores.json (scripts/precomputar_descriptores.py) como
    { id_catalogo: descriptores }. Devuelve None si el archivo no existe
    (entonces los descriptores avanzados se calculan sobre la marcha).
    """
    global _cache_descripciones_pre
    if _cache_descripciones_pre:
        return _cache_descripciones_pre
    if not os.path.exists(DESCRIPTORES_JSON):
        print("[search_engine_hito2] AVISO: no existe data/descriptores.json; "
              "descriptores avanzados se calculan on-the-fly.")
        _cache_descripciones_pre = None
        return None
    try:
        with open(DESCRIPTORES_JSON, "r", encoding="utf-8") as f:
            datos = json.load(f)
        mapa = {}
        for cid, desc in zip(datos.get("ids", []), datos.get("descriptores", [])):
            mapa[str(cid)] = desc
        _cache_descripciones_pre = mapa
        print(f"[search_engine_hito2] {len(mapa)} descriptores avanzados "
              "precomputados cargados.")
        return mapa
    except Exception as e:
        print(f"[search_engine_hito2] AVISO: no se pudo cargar descriptores.json: {e}")
        _cache_descripciones_pre = None
        return None


def _resolver_imagen(nombre_archivo, id_catalogo=None):
    """
    Devuelve la ruta completa de la imagen en CARPETA_IMAGENES, probando el
    nombre exacto del CSV y el equivalente normalizado <id>.jpg (Sala 1
    convierte todo a .jpg). None si no existe.
    """
    candidatas = [str(nombre_archivo)]
    if id_catalogo:
        candidatas.append(str(id_catalogo) + ".jpg")
    for nombre in candidatas:
        ruta = os.path.join(CARPETA_IMAGENES, nombre)
        if os.path.exists(ruta):
            return ruta
    return None


def _carpeta_imagenes_activa():
    """Carpeta única de imágenes: data/images_normalized/ (todas las
    búsquedas del catálogo salen de esta carpeta, sin excepciones)."""
    return CARPETA_IMAGENES


def _descriptores_avanzados_candidato(cand):
    """
    Descriptores avanzados de un candidato. Usa los precomputados
    (descriptores.json, calculados sobre images_normalized/) cuando existen;
    si no, se calculan desde la imagen real con cache.
    """
    mapa = cargar_descriptores_precomputados()
    if mapa is not None:
        desc = mapa.get(str(cand["id"]))
        if desc is not None:
            return desc
    key = (CARPETA_IMAGENES, str(cand["id"]))
    if key in _cache_avanzados_online:
        return _cache_avanzados_online[key]
    ruta = _resolver_imagen(cand["imagen"], cand["id"])
    bgr = _leer_bgr_desde_ruta(ruta) if ruta else None
    desc = descriptores_de_bgr(bgr) if bgr is not None else None
    _cache_avanzados_online[key] = desc
    return desc


# ─────────────────────────────────────────────
# MOTOR CON RERANKING
# ─────────────────────────────────────────────

def cargar_indice_normalizado(modelo: str = "clip"):
    """
    Carga el índice del Hito 2 (Sala 4) para el modelo indicado:
    data/embeddings_<modelo>.npy + data/ids.npy alineados con products.csv.
    El vector de cada producto corresponde a su imagen NORMALIZADA (Sala 1).
    Devuelve None si el índice "clip" no existe (entonces el motor cae al
    índice del Hito 1). Para "openclip" no hay fallback: si falta el índice
    se lanza ValueError con la instrucción para generarlo.
    """
    if modelo not in INDICES_NORMALIZADOS:
        raise ValueError(
            f"Modelo desconocido '{modelo}'; modelos válidos: "
            f"{list(INDICES_NORMALIZADOS)}"
        )
    if modelo in _cache_indices:
        return _cache_indices[modelo]

    ruta_indice = INDICES_NORMALIZADOS[modelo]
    if not os.path.exists(ruta_indice):
        if modelo == "clip":
            print("[search_engine_hito2] AVISO: no existe embeddings_clip.npy "
                  "(Sala 4); usando el índice CLIP del Hito 1.")
            return None
        raise ValueError(
            f"No existe el índice OpenCLIP en {ruta_indice}. Generalo primero: "
            "python scripts/generar_indices_comparativos.py"
        )

    import pandas as pd

    embeddings = np.load(ruta_indice).astype(np.float32)

    # Filas válidas: un vector nulo (imagen fallida en la generación) no debe
    # participar en la búsqueda.
    valido = np.linalg.norm(embeddings, axis=1) > 0

    normas = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normas[normas == 0] = 1e-10
    embeddings = embeddings / normas

    ids = None
    if os.path.exists(IDS_NORMALIZADO):
        try:
            ids = np.load(IDS_NORMALIZADO, allow_pickle=True)
        except Exception:
            ids = None

    csv_path = os.path.join(DATADIR, "products.csv")
    df = None
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)

    # Alineación posicional estricta ids.npy <-> products.csv (la misma
    # validación que hacer_generar_indices_comparativos.cargar_ids). Si ids.npy
    # falta, tiene otra longitud o no coincide contenido con el CSV, se
    # reconstruye desde el CSV para no desalinear silenciosamente.
    if ids is None or len(ids) != len(embeddings):
        if df is not None and "id" in df.columns:
            print("[search_engine_hito2] AVISO: ids.npy no coincide; "
                  "reconstruyendo IDs desde products.csv.")
            ids = df["id"].values
        else:
            raise ValueError(
                "No se pudo alinear embeddings_clip.npy con los IDs "
                "(falta ids.npy o products.csv)"
            )
    elif df is not None and "id" in df.columns:
        csv_ids = df["id"].astype(str).values
        if len(ids) != len(csv_ids) or any(
            str(a) != str(b) for a, b in zip(ids, csv_ids)
        ):
            print("[search_engine_hito2] AVISO: ids.npy desactualizado respecto "
                  "a products.csv; reconstruyendo IDs desde el CSV.")
            ids = csv_ids

    _cache_indices[modelo] = (embeddings, np.asarray(ids), df, valido)
    print(f"[search_engine_hito2] Índice normalizado '{modelo}' de Sala 4 "
          f"cargado: {embeddings.shape[0]} productos x {embeddings.shape[1]} dims.")
    return _cache_indices[modelo]


def buscar_en_indice_normalizado(
    query_embedding,
    top_k: int = 5,
    modelo: str = "clip",
) -> list[dict]:
    """
    Búsqueda por similitud coseno contra el índice del Hito 2
    (imágenes normalizadas, Sala 4) del modelo indicado. Contrato de
    respuesta idéntico al del Hito 1: id, nombre, imagen, url, proveedor,
    score.
    """
    indice = cargar_indice_normalizado(modelo=modelo)
    if indice is None:
        # Sin índice de Sala 4 para este modelo: cae al índice del Hito 1
        # (embeddings.npy). Los descriptores visuales SIEMPRE se calculan
        # sobre images_normalized/ (carpeta única de búsqueda).
        return search_similar(query_embedding, top_k=top_k)

    embeddings, ids, df, valido = indice
    v_query = np.array(query_embedding, dtype=np.float32).flatten()
    if v_query.shape[0] != embeddings.shape[1]:
        raise ValueError(
            f"El vector de consulta tiene {v_query.shape[0]} dimensiones, "
            f"se esperaban {embeddings.shape[1]} (índice {modelo} normalizado)"
        )
    norm_q = np.linalg.norm(v_query)
    if norm_q == 0:
        raise ValueError("El vector de consulta no puede ser un vector nulo")
    v_query = v_query / norm_q

    scores = np.dot(embeddings, v_query)
    # Excluir filas inválidas (vectores nulos) del ranking
    scores[~valido] = -np.inf
    top_idx = np.argsort(scores)[::-1][:top_k]

    resultados = []
    for idx in top_idx:
        row = {} if df is None else df.iloc[idx]
        resultados.append({
            "id": str(ids[idx]),
            "nombre": str(row.get("nombre_original", row.get("nombre", ""))),
            "imagen": str(row.get("imagen", "")),
            "url": str(row.get("url", "")),
            "proveedor": str(row.get("proveedor", "Designs Aimari")),
            "score": round(float(scores[idx]), 4),
        })
    return resultados


def _rerank_candidatos(candidatos, query_image, etiqueta_modelo, top_k: int = 5):
    """
    Paso 2 + 3 del motor Hito 2: reordena los candidatos recuperados
    combinando el score de embeddings (min-max por consulta) con los
    descriptores visuales (color global/regiones, estructura 32x32 y
    avanzados: color dominante, gama, patrón, marco, franjas) y aplica el
    umbral dinámico. `etiqueta_modelo` es la etiqueta de `modelo_utilizado`.
    """
    if not candidatos:
        return []

    # ── Normalización del score de embeddings por consulta ───────────────
    # El coseno del modelo depende de la consulta (no vive en la misma escala
    # que los descriptores 0..1). El min-max sobre los candidatos recuperados
    # lo lleva a [0,1] conservando el ORDEN del ranking inicial.
    scores_emb = np.array([c["score"] for c in candidatos], dtype=np.float64)
    smin, smax = float(scores_emb.min()), float(scores_emb.max())
    rango = smax - smin

    def _emb_norm(s):
        if rango < 1e-9:
            return 0.5
        return (s - smin) / rango

    # Descriptores de la consulta, calculados una sola vez
    bgr_consulta = _a_imagen_bgr(query_image)
    q_izq, q_der = _mitades_bgr(bgr_consulta)
    q_hist_global = _histograma_hsv(bgr_consulta)
    q_hist_frente = _histograma_hsv(q_izq)
    q_hist_espalda = _histograma_hsv(q_der)
    q_estructura = _estructura_gris(bgr_consulta)
    q_avanzados = descriptores_de_bgr(bgr_consulta)

    # ── Paso 2: RERANKING VISUAL ─────────────────────────────────────────
    reranked = []
    for cand in candidatos:
        # Score de embeddings crudo y normalizado a [0,1]
        score_embedding = float(cand["score"])
        score_embedding_norm = _emb_norm(score_embedding)

        # Descriptores clásicos (histogramas + estructura) desde el archivo
        desc = _descriptores_de_archivo(cand["imagen"], id_catalogo=cand.get("id"))
        # Descriptores avanzados: precomputados cuando es posible
        desc_av = _descriptores_avanzados_candidato(cand)
        if desc_av is None and desc is not None:
            desc_av = desc.get("avanzados")

        # Si la imagen del candidato no se puede abrir, todos los scores
        # visuales quedan en 0: la búsqueda NO debe romperse por una sola
        # imagen defectuosa.
        if desc is not None:
            score_color_global = _sim_color(q_hist_global, desc["hist_global"])
            score_frente = _sim_color(q_hist_frente, desc["hist_frente"])
            score_espalda = _sim_color(q_hist_espalda, desc["hist_espalda"])
            score_estructura = _correlacion_estructura(q_estructura, desc["estructura"])
        else:
            score_color_global = 0.0
            score_frente = 0.0
            score_espalda = 0.0
            score_estructura = 0.0

        if q_avanzados is not None and desc_av is not None:
            vis = similitudes_visuales(q_avanzados, desc_av)
            score_color_dominante = vis["color_dominante"]
            score_gama = vis["gama"]
            score_patron = vis["patron"]
            score_marco = vis["marco"]
            score_franjas = vis["franjas"]
        else:
            score_color_dominante = 0.0
            score_gama = 0.0
            score_patron = 0.0
            score_marco = 0.0
            score_franjas = 0.0

        score_final = (
            PESOS["embedding"] * score_embedding_norm
            + PESOS["color_global"] * score_color_global
            + PESOS["color_frente"] * score_frente
            + PESOS["color_espalda"] * score_espalda
            + PESOS["estructura"] * score_estructura
            + PESOS["color_dominante"] * score_color_dominante
            + PESOS["gama"] * score_gama
            + PESOS["patron"] * score_patron
            + PESOS["marco"] * score_marco
            + PESOS["franjas"] * score_franjas
        )

        # Componente de color agregado (para reportes y compatibilidad)
        score_color = (
            (PESOS["color_global"] * score_color_global
             + PESOS["color_frente"] * score_frente
             + PESOS["color_espalda"] * score_espalda)
            / max(1e-9, PESOS["color_global"]
                  + PESOS["color_frente"] + PESOS["color_espalda"])
        )

        reranked.append({
            **cand,
            "score_inicial": round(score_embedding, 4),
            "score_embedding": round(score_embedding_norm, 4),
            "score_color_global": round(score_color_global, 4),
            "score_color_frente": round(score_frente, 4),
            "score_color_espalda": round(score_espalda, 4),
            "score_estructura": round(score_estructura, 4),
            "score_color_dominante": round(score_color_dominante, 4),
            "score_gama": round(score_gama, 4),
            "score_patron": round(score_patron, 4),
            "score_marco": round(score_marco, 4),
            "score_franjas": round(score_franjas, 4),
            "score_color": round(score_color, 4),
            "score_reranking": round(float(score_final), 4),
        })

    # Ordenar por score_final descendente
    reranked.sort(key=lambda r: r["score_reranking"], reverse=True)

    # ── Paso 3: UMBRAL DINÁMICO ──────────────────────────────────────────
    # Solo conservamos candidatos cuya calidad esté razonablemente cerca del
    # mejor resultado. Si el 2do candidato está muy por debajo, no lo
    # forzamos: devolvemos menos de top_k en lugar de relleno irrelevante.
    if reranked:
        mejor_score = reranked[0]["score_reranking"]
        limite_corte = mejor_score - MARGEN_CORTE
        reranked = [
            r for r in reranked if r["score_reranking"] >= limite_corte
        ]

    # Recortar a top_k y asignar la posición final
    final = []
    for posicion, r in enumerate(reranked[:top_k], start=1):
        r["posicion_final"] = posicion
        r["modelo_utilizado"] = f"{etiqueta_modelo}+color+estructura+patron+marco+franjas"
        final.append(r)

    return final


def search_similar_reranked(
    query_embedding,
    query_image,
    top_k: int = 5,
    candidatos_iniciales: int = 30,
    modelo: str = "clip",
) -> list[dict]:
    """
    Búsqueda visual con reranking (Hito 2) con un solo modelo de embeddings.

    Paso 1: recuperación amplia contra el índice NORMALIZADO de Sala 4
    (data/embeddings_<modelo>.npy sobre data/images_normalized/), pidiendo
    candidatos_iniciales en vez de top_k directo. `modelo` puede ser "clip"
    (openai/clip-vit-base-patch32), "openclip"
    (laion/CLIP-ViT-B-32-laion2B-s34B-b79K) o "siglip". Si el índice "clip"
    de Sala 4 no existe, cae al índice del Hito 1 (embeddings.npy).
    Paso 2: reranking (ver `_rerank_candidatos`). Los descriptores visuales
    SIEMPRE se calculan sobre data/images_normalized/ (carpeta única de
    búsqueda de imágenes).
    Paso 3: umbral dinámico que permite devolver menos de top_k resultados.
    """
    candidatos = buscar_en_indice_normalizado(
        query_embedding, top_k=candidatos_iniciales, modelo=modelo
    )
    return _rerank_candidatos(candidatos, query_image, etiqueta_modelo=modelo)


def recuperacion_fusion(
    query_embeddings: dict,
    top_k: int = 100,
    modelos=("clip", "openclip", "siglip"),
) -> list[dict]:
    """
    Recuperación amplia robusta fusionando varios modelos de embeddings.

    Los índices de Sala 4 están alineados posición a posición (mismo orden
    que products.csv), así que se pueden sumar los cosenos de cada modelo
    POR PRODUCTO sin desalinear los IDs. El score fusionado es el promedio
    de los modelos disponibles (los que tengan embedding de consulta e
    índice).

    Cada embedding de consulta puede ser UN vector o una LISTA de vectores
    (recortes de la imagen: imagen completa + cuadrantes). Con varios
    recortes, el score de cada producto es el MÁXIMO sobre los recortes:
    así, si un "punto grande" tapa el diseño en un recorte, otro recorte
    que no lo tenga sigue reconociendo el producto (robustez a oclusión).
    """
    scores_totales = None
    ids_uso = None
    df_uso = None
    for modelo in modelos:
        emb_q = query_embeddings.get(modelo)
        if emb_q is None:
            continue
        indice = cargar_indice_normalizado(modelo=modelo)
        if indice is None:
            continue
        embeddings, ids, df, valido = indice

        # Normaliza un vector de consulta y devuelve sus cosenos
        def _cosenos(v_query):
            v_query = np.array(v_query, dtype=np.float32).flatten()
            if v_query.shape[0] != embeddings.shape[1]:
                raise ValueError(
                    f"El vector de consulta de '{modelo}' tiene "
                    f"{v_query.shape[0]} dimensiones, se esperaban "
                    f"{embeddings.shape[1]}."
                )
            norm_q = np.linalg.norm(v_query)
            if norm_q == 0:
                raise ValueError(f"El vector de consulta de '{modelo}' es nulo")
            s = np.dot(embeddings, v_query / norm_q)
            s[~valido] = np.nan
            return s

        if isinstance(emb_q, (list, tuple)):
            if not emb_q:
                continue
            scores_modelo = np.nanmax(
                np.stack([_cosenos(v) for v in emb_q], axis=1), axis=1
            )
        else:
            scores_modelo = _cosenos(emb_q)

        if scores_totales is None:
            scores_totales = scores_modelo.astype(np.float64)
            ids_uso = np.asarray(ids)
            df_uso = df
        else:
            if len(scores_totales) != len(scores_modelo):
                raise ValueError(
                    "Los índices de la fusión no tienen el mismo largo "
                    f"({len(scores_totales)} vs {len(scores_modelo)})."
                )
            scores_totales = np.nanmean(
                np.stack([scores_totales, scores_modelo], axis=1), axis=1
            )

    if scores_totales is None:
        raise ValueError(
            "No hay embeddings de consulta ni índices disponibles para la fusión."
        )

    # Los productos con TODOS los modelos inválidos quedan fuera
    scores_totales = np.where(np.isnan(scores_totales), -np.inf, scores_totales)
    top_idx = np.argsort(scores_totales)[::-1][:top_k]

    resultados = []
    for idx in top_idx:
        row = {} if df_uso is None else df_uso.iloc[idx]
        resultados.append({
            "id": str(ids_uso[idx]),
            "nombre": str(row.get("nombre_original", row.get("nombre", ""))),
            "imagen": str(row.get("imagen", "")),
            "url": str(row.get("url", "")),
            "proveedor": str(row.get("proveedor", "Designs Aimari")),
            "score": round(float(scores_totales[idx]), 4),
        })
    return resultados


def search_similar_reranked_fusion(
    query_embeddings: dict,
    query_image,
    top_k: int = 5,
    candidatos_iniciales: int = 100,
    modelos=("clip", "openclip", "siglip"),
) -> list[dict]:
    """
    Motor Hito 2 robusto a oclusiones: recuperación amplia por FUSIÓN de
    modelos (CLIP + OpenCLIP + SigLIP) y el mismo reranking visual.

    La fusión promedia por producto los cosenos de cada modelo alineado, y
    con multi-recorte (imagen completa + cuadrantes, máximo por recorte)
    tolera que un "punto grande" u otro elemento tape parte del diseño: si
    un recorte contiene el punto, los demás lo compensan. Luego el reranking
    visual de `_rerank_candidatos` ordena el Top 5 final.
    """
    candidatos = recuperacion_fusion(
        query_embeddings, top_k=candidatos_iniciales, modelos=modelos
    )
    etiqueta = "+".join(modelos)
    return _rerank_candidatos(candidatos, query_image, etiqueta_modelo=etiqueta)
