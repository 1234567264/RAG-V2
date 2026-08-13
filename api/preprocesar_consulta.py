# -*- coding: utf-8 -*-
"""
preprocesar_consulta.py (Sala 2 - Hito 2)
-------------------------------------------
Modulo que prepara la imagen de consulta del usuario ANTES de generar el
embedding. Complementa el trabajo de Sala 1:

    Sala 1 limpia el BANCO (imagenes del catalogo).
    Sala 2 limpia la CONSULTA (imagen que entrega el usuario).

Pipeline:
    imagen del usuario
        -> deteccion de la region de interes (camiseta)
             - remocion de fondo (U2-Net via rembg) con fallback GrabCut (OpenCV)
        -> recorte al area del diseno
        -> centrado sobre lienzo cuadrado
        -> redimension a un tamano uniforme
        -> imagen lista para generar embedding

Cubre los casos del Hito 2: camiseta limpia, sin marco, con fondo, mockup,
persona usando la camiseta, recortada, parte del frente, color modificado,
ligeramente girada y baja calidad.

Integrado en el repositorio principal en api/preprocesar_consulta.py.

Uso:
    from api.preprocesar_consulta import preparar_consulta
    resultado = preparar_consulta(bytes_de_la_imagen)
    resultado["procesada"].save("consulta_limpia.jpg")
"""

import io
import time

import numpy as np
from PIL import Image

try:
    import cv2
    _HAVE_CV2 = True
except Exception:
    _HAVE_CV2 = False

try:
    from rembg import new_session, remove
    _HAVE_REMBG = True
except Exception:
    _HAVE_REMBG = False

TAMANO = 320
_rembg_session = None


def _sesion_rembg():
    """Session U2-Net unica de rembg (se descarga la primera vez)."""
    global _rembg_session
    if _rembg_session is None:
        _rembg_session = new_session("u2net")
    return _rembg_session


def _mascara_rembg(im):
    """Mascara de primer plano (0..255) usando U2-Net."""
    out = remove(im, session=_sesion_rembg())
    alpha = out.split()[-1]
    return np.asarray(alpha, dtype=np.uint8)


def _mascara_grabcut(im):
    """Mascara de primer plano con GrabCut de OpenCV (fallback sin red)."""
    arr = np.asarray(im.convert("RGB"))
    h, w = arr.shape[:2]
    rect = (int(w * 0.03), int(h * 0.03), int(w * 0.94), int(h * 0.94))
    mask = np.zeros((h, w), dtype=np.uint8)
    bgd = np.zeros((1, 65), dtype=np.float64)
    fgd = np.zeros((1, 65), dtype=np.float64)
    cv2.grabCut(arr, mask, rect, bgd, fgd, 3, cv2.GC_INIT_WITH_RECT)
    mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    return mask


def _recortar_bordes(im, tol=5, frac=0.12):
    """
    Recorta bandas casi uniformes del borde (fondo liso) para ayudar a la
    segmentacion y al caso "sin marco". Devuelve (imagen, (x1,y1,x2,y2)).
    """
    arr = np.asarray(im.convert("RGB"))
    h, w = arr.shape[:2]

    def flat_rows(rows):
        rng = rows.max(axis=(1, 2)) - rows.min(axis=(1, 2))
        return rng < tol

    top = int(h * frac)
    r_top = arr[:top]
    rows_top = flat_rows(r_top) if len(r_top) else np.zeros(0, dtype=bool)
    n_top = int(rows_top.sum())

    bot = int(h * frac)
    r_bot = arr[h - bot:]
    rows_bot = flat_rows(r_bot) if len(r_bot) else np.zeros(0, dtype=bool)
    n_bot = int(rows_bot.sum())

    y1 = n_top if n_top > max(1, top * 0.6) else 0
    y2 = h - n_bot if n_bot > max(1, bot * 0.6) else h

    arr_c = arr[y1:y2]
    hc = y2 - y1
    if hc <= 0:
        return im, (0, 0, w, h)

    def flat_cols(cols):
        rng = cols.max(axis=(0, 2)) - cols.min(axis=(0, 2))
        return rng < tol

    lef = int(w * frac)
    r_lef = arr_c[:, :lef]
    cols_lef = flat_cols(r_lef) if r_lef.size else np.zeros(0, dtype=bool)
    n_lef = int(cols_lef.sum())

    rig = int(w * frac)
    r_rig = arr_c[:, -rig:]
    cols_rig = flat_cols(r_rig) if r_rig.size else np.zeros(0, dtype=bool)
    n_rig = int(cols_rig.sum())

    x1 = n_lef if n_lef > max(1, lef * 0.6) else 0
    x2 = w - n_rig if n_rig > max(1, rig * 0.6) else w

    if (x2 - x1) < w * 0.5 or (y2 - y1) < h * 0.5:
        return im, (0, 0, w, h)

    return im.crop((x1, y1, x2, y2)), (x1, y1, x2, y2)


def _bbox(mask, margen=0.04, umbral=20):
    """Bounding box del primer plano sobre la mascara."""
    ys, xs = np.where(mask > umbral)
    if len(xs) == 0:
        return None
    h, w = mask.shape
    x1, x2 = int(xs.min()), int(xs.max())
    y1, y2 = int(ys.min()), int(ys.max())
    mx = int(w * margen)
    my = int(h * margen)
    x1, y1 = max(0, x1 - mx), max(0, y1 - my)
    x2, y2 = min(w, x2 + mx), min(h, y2 + my)
    return (x1, y1, x2, y2)


def _centrar_y_redimensionar(crop, tamano=TAMANO):
    """Pega el recorte centrado en un lienzo cuadrado blanco y lo redimensiona."""
    w, h = crop.size
    lado = max(w, h)
    lienzo = Image.new("RGB", (lado, lado), (255, 255, 255))
    lienzo.paste(crop, ((lado - w) // 2, (lado - h) // 2))
    return lienzo.resize((tamano, tamano), Image.LANCZOS)


def preparar_consulta(datos, tamano=TAMANO):
    """
    Prepara una imagen de consulta.

    Parametros
    ----------
    datos : bytes o PIL.Image
        Imagen del usuario.
    tamano : int
        Tamano del lienzo de salida (por defecto 320x320).

    Devuelve
    --------
    dict con:
        original       : PIL.Image (consulta tal como llego)
        procesada      : PIL.Image (consulta limpia para embedding)
        pasos          : list[str] pasos aplicados
        backend        : str ('rembg' | 'grabcut' | 'ninguno')
        bbox           : tuple o None
        recorte_pct    : float (fraccion de la imagen conservada)
        tiempo_segundos: float
    """
    t0 = time.time()
    if isinstance(datos, Image.Image):
        im = datos.convert("RGB")
    else:
        im = Image.open(io.BytesIO(datos)).convert("RGB")

    pasos = []

    im_c, recorte = _recortar_bordes(im)
    if recorte != (0, 0, im.width, im.height):
        pasos.append("recortar_bordes")

    mascara = None
    backend = "ninguno"
    if _HAVE_REMBG:
        try:
            mascara = _mascara_rembg(im_c)
            backend = "rembg"
        except Exception:
            mascara = None
    if mascara is None and _HAVE_CV2:
        try:
            mascara = _mascara_grabcut(im_c)
            backend = "grabcut"
        except Exception:
            mascara = None
    if mascara is not None:
        pasos.append(f"remover_fondo:{backend}")

    bbox = _bbox(mascara) if mascara is not None else None
    if bbox is None:
        pasos.append("recorte_directo")
        procesada = _centrar_y_redimensionar(im_c, tamano)
        recorte_pct = 1.0
    else:
        x1, y1, x2, y2 = bbox
        ancho, alto = im_c.size
        recorte_pct = ((x2 - x1) * (y2 - y1)) / (ancho * alto)
        pasos.append(f"recortar_region:{x1},{y1},{x2},{y2}")
        if recorte_pct < 0.99:
            crop = im_c.crop(bbox)
            procesada = _centrar_y_redimensionar(crop, tamano)
        else:
            pasos.append("centrar_sin_recorte")
            procesada = _centrar_y_redimensionar(im_c, tamano)

    return {
        "original": im,
        "procesada": procesada,
        "pasos": pasos,
        "backend": backend,
        "bbox": bbox,
        "recorte_pct": round(float(recorte_pct), 4),
        "tiempo_segundos": round(time.time() - t0, 3),
    }
