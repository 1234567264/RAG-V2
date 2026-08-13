# -*- coding: utf-8 -*-
"""
descriptores_visuales.py
------------------------
Descriptores visuales avanzados para la comparacion de camisetas deportivas.

Complementa el reranking de api/search_engine_hito2.py con atributos que una
persona usa para juzgar dos camisetas "a simple vista":

  * COLOR DOMINANTE / GAMA CROMATICA : colores principales del diseno
    (k-means sobre HSV) y su distribucion global (histograma HSV grueso).
  * DISENO / PATRON PRINCIPAL       : energia de textura en una grilla
    (variacion local en grises), robusta al color.
  * ESTRUCTURA (con/sin marcos)     : deteccion de banda perimetral uniforme
    (marco de la tarjeta original o borde de fondo).
  * ELEMENTOS GRAFICOS ESPECIFICOS  : franjas/rayas horizontales y verticales
    (periodicidad del perfil de brillo) y contraste de una banda central
    ("rayado en medio").

Todas las similitudes devuelven valores en [0, 1] (1 = identicos).

Los calculos se hacen con numpy puro (solo imagen en grises y conversiones de
color); OpenCV se usa si esta disponible para acelerar la conversion. Las
imagenes se abren con PIL para tolerar rutas con caracteres no-ASCII (el mismo
motivo por el que api/search_engine_hito2.py lee con PIL y no con cv2.imread).
"""

import numpy as np
from PIL import Image

try:
    import cv2
    _HAVE_CV2 = True
except Exception:
    _HAVE_CV2 = False

K_COLORES = 4           # numero de colores dominantes (k-means)
BINS_GAMA = (8, 4, 4)   # bins del histograma de gama cromatica (H, S, V)
GRID_PATRON = 8         # grilla de textura (GRID x GRID)
MUESTREO_MAX = 2000     # pixeles maximo para el k-means de colores


def leer_bgr_desde_ruta(ruta):
    """Lee una imagen desde disco como arreglo BGR (tolerante a rutas no-ASCII)."""
    try:
        im = Image.open(ruta).convert("RGB")
    except Exception:
        return None
    # RGB -> BGR invirtiendo el eje de canales (sin depender de OpenCV)
    return np.asarray(im)[:, :, ::-1]


# ─────────────────────────────────────────────
# UTILIDADES DE COLOR
# ─────────────────────────────────────────────

def _a_gris(bgr):
    """Escala de grises (float32) a partir de un arreglo BGR."""
    if bgr is None or bgr.size == 0:
        return np.zeros((0, 0), dtype=np.float32)
    if bgr.ndim == 2:
        return bgr.astype(np.float32)
    if _HAVE_CV2:
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    r = bgr[..., 2].astype(np.float32)
    g = bgr[..., 1].astype(np.float32)
    b = bgr[..., 0].astype(np.float32)
    return 0.299 * r + 0.587 * g + 0.114 * b


def _hsv_numpy(pix):
    """
    Convierte pixeles BGR (N, 3) a HSV. Devuelve (H, S, V), cada canal en [0,1].
    Implementacion numpy pura (sin OpenCV) para no depender de cv2.
    """
    r = pix[..., 2].astype(np.float32) / 255.0
    g = pix[..., 1].astype(np.float32) / 255.0
    b = pix[..., 0].astype(np.float32) / 255.0
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    delta = mx - mn
    h = np.zeros_like(mx)
    s = np.zeros_like(mx)
    v = mx.copy()
    m = delta > 1e-6
    if m.any():
        rc = np.zeros_like(mx)
        gc = np.zeros_like(mx)
        bc = np.zeros_like(mx)
        rc[m] = (mx[m] - r[m]) / delta[m]
        gc[m] = (mx[m] - g[m]) / delta[m]
        bc[m] = (mx[m] - b[m]) / delta[m]
        cond_r = (mx == r) & m
        cond_g = (~cond_r) & (mx == g)
        h = np.where(cond_r, bc - gc, np.where(cond_g, 2.0 + rc - bc, 4.0 + gc - rc))
        h = (h % 6.0) / 6.0
        s[m] = delta[m] / mx[m]
    return h, s, v


def _a_hsv(bgr):
    """Convierte un arreglo BGR completo a (H, S, V) con cada canal en [0,1]."""
    if _HAVE_CV2:
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        h = hsv[..., 0].astype(np.float32) / 180.0
        s = hsv[..., 1].astype(np.float32) / 255.0
        v = hsv[..., 2].astype(np.float32) / 255.0
        return h, s, v
    h, s, v = _hsv_numpy(bgr.reshape(-1, 3))
    return h.reshape(bgr.shape[:2]), s.reshape(bgr.shape[:2]), v.reshape(bgr.shape[:2])


def _muestrear_pixeles(bgr):
    """Muestrea la imagen (como maximo MUESTREO_MAX pixeles) para el k-means."""
    pix = bgr.reshape(-1, 3).astype(np.float32)
    if len(pix) <= MUESTREO_MAX:
        return pix
    paso = int(np.sqrt(len(pix) / MUESTREO_MAX)) or 1
    return bgr[::paso, ::paso].reshape(-1, 3).astype(np.float32)


def _kmeans(pix, k=K_COLORES, iteraciones=8):
    """
    k-means sencillo (Lloyd) sobre pixeles (H, S, V) en [0,1].
    Devuelve (centros, pesos) con los centros ordenados por el indice original.
    """
    rng = np.random.RandomState(0)
    if len(pix) <= k:
        centros = pix.copy()
        pesos = np.ones(k, dtype=np.float32) / k
        return centros, pesos
    idx = rng.choice(len(pix), k, replace=False)
    centros = pix[idx].copy()
    for _ in range(iteraciones):
        d = np.abs(pix[:, None, :] - centros[None, :, :]).sum(axis=2)
        etiq = d.argmin(axis=1)
        nuevos = []
        for j in range(k):
            grupo = pix[etiq == j]
            nuevos.append(grupo.mean(axis=0) if len(grupo) else centros[j])
        nuevos = np.array(nuevos, dtype=np.float32)
        if np.allclose(nuevos, centros, atol=1e-4):
            centros = nuevos
            break
        centros = nuevos
    etiq = np.abs(pix[:, None, :] - centros[None, :, :]).sum(axis=2).argmin(axis=1)
    pesos = np.bincount(etiq, minlength=k) / max(1, len(etiq))
    return centros, pesos.astype(np.float32)


# ─────────────────────────────────────────────
# DESCRIPTORES
# ─────────────────────────────────────────────

def colores_dominantes(bgr, k=K_COLORES):
    """
    Colores dominantes de la imagen en (H, S, V) con su peso (fraccion de
    pixeles). Devueltos de mayor a menor peso, cada campo en [0,1].
    """
    pix = _muestrear_pixeles(bgr)
    h, s, v = _hsv_numpy(pix)
    datos = np.stack([h, s, v], axis=1).astype(np.float32)
    centros, pesos = _kmeans(datos, k)
    orden = np.argsort(pesos)[::-1]
    return [
        {
            "h": float(centros[i, 0]),
            "s": float(centros[i, 1]),
            "v": float(centros[i, 2]),
            "peso": float(pesos[i]),
        }
        for i in orden
    ]


def histograma_gama(bgr, bins=BINS_GAMA):
    """
    Histograma HSV grueso normalizado (la "gama cromatica" global).
    Devuelve un arreglo plano de largo bins[0]*bins[1]*bins[2].
    """
    h, s, v = _a_hsv(bgr)
    bh, bs, bv = bins
    hb = np.clip((h * bh).astype(np.int64), 0, bh - 1)
    sb = np.clip((s * bs).astype(np.int64), 0, bs - 1)
    vb = np.clip((v * bv).astype(np.int64), 0, bv - 1)
    idx = hb * (bs * bv) + sb * bv + vb
    hist = np.bincount(idx.ravel(), minlength=bh * bs * bv).astype(np.float32)
    tot = hist.sum()
    if tot > 0:
        hist = hist / tot
    return hist


def _reducir_bloques(a, grid):
    """Promedio por bloques grid x grid de una imagen 2D."""
    h, w = a.shape
    ph, pw = h // grid, w // grid
    if ph == 0 or pw == 0:
        return np.zeros((grid, grid), dtype=np.float32)
    hc, wc = ph * grid, pw * grid
    cortada = a[:hc, :wc]
    return cortada.reshape(grid, ph, grid, pw).mean(axis=(1, 3)).astype(np.float32)


def patron_textura(bgr, grid=GRID_PATRON):
    """
    Descriptor de diseno/patron: energia de variacion local (Laplaciano o
    gradiente) promediada en una grilla grid x grid y normalizada. Representa
    la textura del diseno independiente del color.
    """
    gris = _a_gris(bgr)
    if gris.size == 0:
        return np.zeros(grid * grid, dtype=np.float32).tolist()
    if _HAVE_CV2:
        energia = np.abs(cv2.Laplacian(gris, cv2.CV_32F))
    else:
        gy, gx = np.gradient(gris)
        energia = np.hypot(gx, gy)
    bloque = _reducir_bloques(energia, grid)
    media = bloque.mean()
    desv = bloque.std()
    if desv < 1e-6:
        return np.zeros(grid * grid, dtype=np.float32).tolist()
    norm = ((bloque - media) / (3.0 * desv)).clip(0.0, 1.0)
    return norm.ravel().tolist()


def detectar_marco(bgr, frac=0.04):
    """
    Deteccion de estructura "con/sin marco": compara una banda perimetral de
    ancho frac*min(h,w) contra el interior. Un lado cuenta como marco si es
    casi uniforme (desv. baja) y claramente distinto del contenido (diferencia
    de brillo alta). Devuelve la fraccion de lados con marco (0..1).
    """
    h, w = bgr.shape[:2]
    if min(h, w) < 12:
        return {"fraccion_marco": 0.0, "tiene_marco": False}
    gris = _a_gris(bgr)
    t = max(2, int(min(h, w) * frac))
    if t >= h // 2 or t >= w // 2:
        return {"fraccion_marco": 0.0, "tiene_marco": False}
    interior = gris[t:h - t, t:w - t]
    if interior.size == 0:
        return {"fraccion_marco": 0.0, "tiene_marco": False}
    med_int = float(interior.mean())
    lados = 0
    for banda in (gris[:t, :], gris[h - t:, :], gris[:, :t], gris[:, w - t:]):
        if banda.size == 0:
            continue
        if float(banda.std()) < 20 and abs(float(banda.mean()) - med_int) > 14:
            lados += 1
    fraccion = lados / 4.0
    return {"fraccion_marco": round(fraccion, 4), "tiene_marco": fraccion >= 0.5}


def _periodicidad(perfil):
    """
    Mide que tan periodico es un perfil de brillo (0..1): razon entre el pico
    del espectro (excluyendo DC) y la energia total. Un patron a franjas
    concentra la energia en una frecuencia -> valor alto.
    """
    p = perfil - perfil.mean()
    n = len(p)
    if n < 8 or p.std() < 1e-3:
        return 0.0
    fft = np.abs(np.fft.rfft(p))
    fft[0] = 0.0
    total = fft.sum()
    if total <= 1e-9:
        return 0.0
    return float(min(1.0, fft.max() / total))


def detectar_franjas(bgr):
    """
    Elementos graficos especificos: franjas/rayas horizontales y verticales
    (periodicidad del perfil de brillo en la region central) y contraste de
    una banda central ("rayado en medio"). Todo en [0,1].
    """
    gris = _a_gris(bgr)
    h, w = gris.shape
    y0, y1 = int(h * 0.15), int(h * 0.85)
    x0, x1 = int(w * 0.15), int(w * 0.85)
    if y1 - y0 < 8 or x1 - x0 < 8:
        return {"franjas_horizontales": 0.0, "franjas_verticales": 0.0, "banda_central": 0.0}
    region = gris[y0:y1, x0:x1]
    perfil_filas = region.mean(axis=1)  # variacion en filas -> franjas horizontales
    perfil_cols = region.mean(axis=0)   # variacion en columnas -> franjas verticales
    score_h = _periodicidad(perfil_filas)
    score_v = _periodicidad(perfil_cols)
    mitad = region.shape[0] // 2
    banda = region[max(0, mitad - 2):mitad + 2, :]
    contraste = float(abs(banda.mean() - region.mean()) / 128.0)
    return {
        "franjas_horizontales": round(min(1.0, score_h), 4),
        "franjas_verticales": round(min(1.0, score_v), 4),
        "banda_central": round(min(1.0, contraste), 4),
    }


def descriptores_de_bgr(bgr):
    """
    Descriptores completos de una imagen BGR. Devuelve un dict serializable
    (JSON-friendly) o None si la imagen no es valida.
    """
    if bgr is None or bgr.size == 0:
        return None
    if bgr.ndim == 2:
        bgr = np.repeat(bgr[:, :, None], 3, axis=2)
    return {
        "color_dominante": colores_dominantes(bgr),
        "gama": histograma_gama(bgr).tolist(),
        "patron": patron_textura(bgr),
        "marco": detectar_marco(bgr),
        "franjas": detectar_franjas(bgr),
    }


# ─────────────────────────────────────────────
# SIMILITUDES POR ATRIBUTO (todas en [0, 1])
# ─────────────────────────────────────────────

def _correlacion(a, b):
    """Coeficiente de correlacion de Pearson recortado a [0,1].

    Si ambos descriptores carecen de variacion (p. ej. un diseno liso produce
    un vector de textura nulo), se consideran iguales: dos camisetas lisas
    coinciden en patron aunque la correlacion no este definida.
    """
    a = np.asarray(a, dtype=np.float32).ravel()
    b = np.asarray(b, dtype=np.float32).ravel()
    if len(a) != len(b):
        return 0.0
    std_a, std_b = a.std(), b.std()
    if std_a < 1e-9 and std_b < 1e-9:
        return 1.0
    if std_a < 1e-9 or std_b < 1e-9:
        return 0.0
    return float(max(0.0, min(1.0, float(np.corrcoef(a, b)[0, 1]))))


def _vector_colores(dom, n_bins=8):
    """
    Convierte los colores dominantes a un histograma de "nombres de color":
    los tonos cromaticos (por bin de H) mas un bucket de neutros (baja
    saturacion o luminosidad). Asi dos camisetas recoloreadas del mismo diseno
    siguen coincidiendo si conservan el "tipo" de color.
    """
    v = np.zeros(n_bins + 1, dtype=np.float32)
    for d in dom or []:
        if d["s"] < 0.18 or d["v"] < 0.12:
            v[0] += d["peso"]
        else:
            b = 1 + int(min(n_bins - 1, max(0.0, d["h"]) * n_bins))
            v[b] += d["peso"]
    return v


def sim_color_dominante(q, c, n_bins=8):
    return _correlacion(_vector_colores(q, n_bins), _vector_colores(c, n_bins))


def sim_gama(q, c):
    return _correlacion(q, c)


def sim_patron(q, c):
    return _correlacion(q, c)


def sim_marco(q, c):
    fq = (q or {}).get("fraccion_marco", 0.0)
    fc = (c or {}).get("fraccion_marco", 0.0)
    return float(max(0.0, min(1.0, 1.0 - abs(fq - fc))))


def sim_franjas(q, c):
    def _get(d, k):
        return (d or {}).get(k, 0.0)
    return float(max(0.0, min(1.0, 1.0
        - 0.5 * abs(_get(q, "franjas_horizontales") - _get(c, "franjas_horizontales"))
        - 0.25 * abs(_get(q, "franjas_verticales") - _get(c, "franjas_verticales"))
        - 0.25 * abs(_get(q, "banda_central") - _get(c, "banda_central")))))


def similitudes_visuales(q, c):
    """Similitudes por atributo entre dos descriptores completos (dict 0..1)."""
    if q is None or c is None:
        return {"color_dominante": 0.0, "gama": 0.0, "patron": 0.0, "marco": 0.0, "franjas": 0.0}
    return {
        "color_dominante": sim_color_dominante(q.get("color_dominante"), c.get("color_dominante")),
        "gama": sim_gama(q.get("gama"), c.get("gama")),
        "patron": sim_patron(q.get("patron"), c.get("patron")),
        "marco": sim_marco(q.get("marco"), c.get("marco")),
        "franjas": sim_franjas(q.get("franjas"), c.get("franjas")),
    }
