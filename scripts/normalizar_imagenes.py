# -*- coding: utf-8 -*-
"""
normalizar_imagenes.py  -  Sala 1 / Hito 2
-------------------------------------------
Normalizacion automatica del banco de imagenes.

Objetivo (TRABAJO.md, Hito 2 - Sala 1):
  Transformar las imagenes del catalogo en imagenes limpias y estandarizadas
  que contengan UNICAMENTE las dos vistas del uniforme (FRENTE + ESPALDA).

Lo que se elimina de cada tarjeta original:
  - cabecera (banda superior con texto/logo de la empresa);
  - pie / URL (banda inferior);
  - marco exterior en los cuatro lados;
  - margenes blancos de la tarjeta;
  - logo / nombre / icono de la empresa del lado izquierdo;
  - separadores y espacios vacios entre uniformes;
  - cualquier contenido ajeno al producto.

Lo que se conserva:
  - el uniforme de frente;
  - el uniforme de espalda;
  - un margen minimo de seguridad para no cortar el borde del producto.

Flujo:
  data/images_final/ (fuente unica, NO se modifica)
        -> deteccion de bandas (cabecera / zona central / pie)
        -> deteccion de bloques verticales en la zona central
        -> identificacion logo / frente / espalda
        -> recorte ajustado al contenido util (frente+espalda)
        -> redimension conservando proporcion (lado mayor = CANVAS_SIZE)
        -> data/images_normalized/ (mismo ID y extension)

Reglas de seguridad:
  - Las imagenes de data/images_final/ permanecen intactas.
  - Se mantienen exactamente los IDs/nombres de archivo originales.
  - Los casos que no se pueden resolver con seguridad se marcan como
    'dudoso' (revision humana) o 'fallido', nunca se fuerzan.

Uso:
    python scripts/normalizar_imagenes.py
    python scripts/normalizar_imagenes.py --limite 200     # solo las primeras 200
    python scripts/normalizar_imagenes.py --canvas 700     # lado mayor del lienzo
"""

import argparse
import csv
import os
import random
import sys
import time
import warnings

import numpy as np
from PIL import Image

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONFIGURACION
# ─────────────────────────────────────────────
BASE_DIR       = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IMAGES_ORIGEN  = os.path.join(BASE_DIR, "data", "images_final")      # fuente unica (no se toca)
IMAGES_NORM    = os.path.join(BASE_DIR, "data", "images_normalized") # salida normalizada
REPORTE_TXT    = os.path.join(BASE_DIR, "data", "informe_normalizacion.txt")
DETALLE_CSV    = os.path.join(BASE_DIR, "data", "detalle_normalizacion.csv")
REVISION_CSV   = os.path.join(BASE_DIR, "data", "revision_humana_50.csv")
CONTACT_SHEET  = os.path.join(BASE_DIR, "data", "revision_contact_sheet.png")

UMBRAL_FONDO   = 245     # pixeles con brillo menor a esto se consideran contenido
FRACCION_BANDA = 0.02    # fraccion minima de fila/columna "no fondo" para iniciar banda/bloque
FUSION_GAP     = 12      # px: bandas/bloques separados por menos de esto se fusionan
ANCHO_LOGO_MAX = 0.18    # fraccion del ancho: bloque izquierdo mas estrecho que esto es logo
HUECO_MIN      = 0.15    # densidad maxima en un "valle" para considerarlo hueco real
CANVAS_SIZE    = 700     # lado mayor del lienzo de salida (proporcion conservada)
AMPLIACION_MAX = 2.0     # no ampliar mas de 2x (evitar perdida de definicion)
EXTENSIONES    = (".jpg", ".jpeg", ".png", ".gif")


# ─────────────────────────────────────────────
# HELPERS DE IMAGEN
# ─────────────────────────────────────────────

def abrir_rgb(ruta):
    """Abre cualquier imagen (JPG/PNG/GIF, incl. paleta/alfa) como RGB plano."""
    im = Image.open(ruta)
    if im.mode in ("P", "L"):
        im = im.convert("RGBA")
    if im.mode == "RGBA":
        fondo = Image.new("RGB", im.size, (255, 255, 255))
        im = Image.alpha_composite(fondo.convert("RGBA"), im).convert("RGB")
    else:
        im = im.convert("RGB")
    return im


def detector_bandas(a, h):
    """
    Lista de bandas horizontales de contenido (no fondo), fusionando
    franjas separadas por huecos blancos pequenos.
    Cada banda es (y_inicio, y_fin) inclusive.
    """
    fr = (a.mean(axis=2) < UMBRAL_FONDO).mean(axis=1)
    bandas = []
    en_banda = False
    for y, v in enumerate(fr):
        if v > FRACCION_BANDA and not en_banda:
            inicio = y
            en_banda = True
        elif v <= FRACCION_BANDA and en_banda:
            bandas.append((inicio, y - 1))
            en_banda = False
    if en_banda:
        bandas.append((inicio, h - 1))

    fusionadas = []
    for b in bandas:
        if fusionadas and b[0] - fusionadas[-1][1] < FUSION_GAP:
            fusionadas[-1] = (fusionadas[-1][0], b[1])
        else:
            fusionadas.append(list(b))
    return [tuple(b) for b in fusionadas]


def bloques_columnas(seg):
    """
    Bloques verticales de contenido dentro de la zona central.
    Cada bloque es (x_inicio, x_fin) inclusive; los huecos pequenos
    (menores a FUSION_GAP) se fusionan.

    El perfil de densidad se SUAVIZA con una ventana adaptativa (~3% del
    ancho) para que las telas a rayas o con textura fina no fragmenten
    artificialmente un mismo uniforme en varios bloques.
    """
    fr = (seg.mean(axis=2) < UMBRAL_FONDO).mean(axis=0)
    ventana = max(3, int(0.03 * seg.shape[1]) | 1)
    kernel = np.ones(ventana) / ventana
    fr = np.convolve(fr, kernel, mode="same")
    bloques = []
    en = False
    for x, v in enumerate(fr):
        if v > FRACCION_BANDA and not en:
            inicio = x
            en = True
        elif v <= FRACCION_BANDA and en:
            bloques.append((inicio, x - 1))
            en = False
    if en:
        bloques.append((inicio, seg.shape[1] - 1))
    fusionados = []
    for b in bloques:
        if fusionados and b[0] - fusionados[-1][1] < FUSION_GAP:
            fusionados[-1] = (fusionados[-1][0], b[1])
        else:
            fusionados.append(list(b))
    return [tuple(b) for b in fusionados]


def perfil_densidad(seg):
    """Fraccion de filas no-fondo por columna dentro de la zona central."""
    return (seg.mean(axis=2) < UMBRAL_FONDO).mean(axis=0)


def buscar_hueco(fr, x0, x1, margen_frac=0.20, umbral=HUECO_MIN):
    """
    Busca el punto de menor densidad dentro de [x0, x1] que sea un hueco
    real (densidad < umbral) y no este pegado a los extremos.
    Devuelve la columna del minimo, o None si no hay hueco claro.
    """
    trozo = fr[x0 : x1 + 1]
    if len(trozo) < 3:
        return None
    margen = int(margen_frac * len(trozo))
    if 2 * margen >= len(trozo):
        return None
    central = trozo[margen:-margen]
    idx = int(np.argmin(central)) + margen
    if trozo[idx] > umbral:
        return None
    return x0 + idx


def separar_logo_y_frente(fr, x0, x1, ancho_logo_max):
    """
    Cuando el primer bloque es ancho y empieza en el borde izquierdo de la
    tarjeta, puede contener el logo fusionado con el frente. Busca el hueco
    interno cercano al inicio; si la parte izquierda resultante es estrecha,
    la devuelve como logo y el resto como frente.
    Devuelve (logo, frente) o (None, (x0, x1)) si no hay separacion clara.
    """
    ancho = x1 - x0 + 1
    # el logo, si existe, esta en el 40% izquierdo del bloque
    zona = x0 + int(0.40 * ancho)
    hueco = buscar_hueco(fr, x0, zona, margen_frac=0.15)
    if hueco is None:
        return None, (x0, x1)
    logo = (x0, hueco - 1)
    frente = (hueco + 1, x1)
    if (logo[1] - logo[0] + 1) > ancho_logo_max:
        return None, (x0, x1)
    return logo, frente


def detectar_uniformes(seg, ancho_banda):
    """
    Detecta las regiones FRENTE y ESPALDA dentro de la zona central.

    Devuelve:
      (frente, espalda, detalles)
      frente  : (x0, x1) del frente o None
      espalda : (x0, x1) de la espalda o None
      detalles: lista de textos para el reporte
    """
    det = []
    fr = perfil_densidad(seg)
    bloques = bloques_columnas(seg)

    # descartar ruido (bloques de 1-2 px)
    bloques = [b for b in bloques if (b[1] - b[0] + 1) >= 0.01 * ancho_banda]
    if not bloques:
        return None, None, ["sin bloques de contenido"]

    ancho_logo_max = ANCHO_LOGO_MAX * ancho_banda
    umbral_borde = 0.05 * ancho_banda  # bloque pegado al borde izquierdo

    primero = bloques[0]
    ancho_primero = primero[1] - primero[0] + 1

    # ── caso A: primer bloque estrecho a la izquierda -> logo ──
    if len(bloques) >= 2 and ancho_primero <= ancho_logo_max:
        logo = bloques.pop(0)
        det.append(f"logo descartado x[{logo[0]}:{logo[1]}]")

    # ── caso B: primer bloque ancho pegado al borde -> puede tener logo dentro ──
    elif (len(bloques) >= 1 and primero[0] <= umbral_borde
          and ancho_primero > ancho_logo_max):
        logo, frente_nuevo = separar_logo_y_frente(fr, primero[0], primero[1],
                                                   ancho_logo_max)
        if logo is not None:
            bloques[0] = frente_nuevo
            det.append(f"logo separado de bloque ancho x[{logo[0]}:{logo[1]}]")

    # ── separar frente y espalda si quedaron fusionados ──
    if len(bloques) == 1:
        x0, x1 = bloques[0]
        hueco = buscar_hueco(fr, x0, x1)
        if hueco is not None:
            bloques = [(x0, hueco - 1), (hueco + 1, x1)]
            det.append(f"frente/espalda fusionados, separados en x={hueco}")

    frente = bloques[0] if len(bloques) >= 1 else None
    espalda = bloques[1] if len(bloques) >= 2 else None

    # validacion de tamanos minimos
    min_bloque = 0.12 * ancho_banda
    if frente is not None and (frente[1] - frente[0] + 1) < min_bloque:
        frente = None
    if espalda is not None and (espalda[1] - espalda[0] + 1) < min_bloque:
        espalda = None

    return frente, espalda, det


def ajustar_recorte(seg, x0, x1, y0, y1, margen=2):
    """
    Ajusta el bounding box al contenido util real (sin margenes ni marco),
    dejando solo un margen de seguridad minimo. Devuelve (x0,x1,y0,y1)
    en coordenadas de la imagen original.

    Nota: seg recorre todo el ancho de la imagen, por lo que sus columnas
    ya estan en coordenadas de la imagen; solo las filas necesitan
    desplazamiento (+y0).
    """
    mask = (seg[:, x0 : x1 + 1].mean(axis=2) < UMBRAL_FONDO)
    cols = np.where(mask.any(axis=0))[0]
    rows = np.where(mask.any(axis=1))[0]
    if len(cols) == 0 or len(rows) == 0:
        return x0, x1, y0, y1

    fx0 = int(cols.min()) + x0
    fx1 = int(cols.max()) + x0
    fy0 = int(rows.min())
    fy1 = int(rows.max())
    fx0 = max(x0, fx0 - margen)
    fx1 = min(x1, fx1 + margen)
    fy0 = max(0, fy0 - margen)
    fy1 = min(seg.shape[0] - 1, fy1 + margen)
    return fx0, fx1, fy0 + y0, fy1 + y0


def recortar_franjas_oscuras(im, umbral=40, dif=30, fraccion_max=0.04):
    """
    Elimina franjas oscuras delgadas (bordes/marco residuales de la tarjeta
    original) pegadas a cualquiera de los 4 lados del recorte, para que el
    contenido llene la imagen. Solo recorta si la franja es realmente oscura
    en comparacion con el contenido interior y no excede una fraccion maxima.
    """
    a = np.asarray(im.convert("RGB"), dtype=np.float32)
    h, w, _ = a.shape
    brillo = a.mean(axis=2)
    if min(h, w) < 6:
        return im

    max_px_col = max(1, int(fraccion_max * w))
    max_px_fil = max(1, int(fraccion_max * h))

    izq = 0
    der = 0
    if w > 12:
        col = brillo.mean(axis=0)
        interior = col[int(0.03 * w):int(0.08 * w)].mean()
        while izq < max_px_col and col[izq] < umbral and col[izq] < interior - dif:
            izq += 1
        if izq < 2:
            izq = 0
        while der < max_px_col and col[w - 1 - der] < umbral and col[w - 1 - der] < interior - dif:
            der += 1
        if der < 2:
            der = 0

    sup = 0
    inf = 0
    if h > 12:
        fil = brillo.mean(axis=1)
        interior = fil[int(0.03 * h):int(0.08 * h)].mean()
        while sup < max_px_fil and fil[sup] < umbral and fil[sup] < interior - dif:
            sup += 1
        if sup < 2:
            sup = 0
        while inf < max_px_fil and fil[h - 1 - inf] < umbral and fil[h - 1 - inf] < interior - dif:
            inf += 1
        if inf < 2:
            inf = 0

    if izq or der or sup or inf:
        x0 = izq
        x1 = w - der
        y0 = sup
        y1 = h - inf
        if x1 - x0 >= 4 and y1 - y0 >= 4:
            return im.crop((x0, y0, x1, y1))
    return im


def normalizar_imagen(ruta):
    """
    Procesa una imagen y devuelve (imagen_normalizada, estado, detalle,
    frente, espalda, n_bandas). estado: 'ok' | 'dudoso' | 'fallido'
    """
    try:
        im = abrir_rgb(ruta)
    except Exception as e:
        return None, "fallido", f"no se pudo abrir: {e}", None, None, 0

    a = np.asarray(im, dtype=np.float32)
    h, w, _ = a.shape

    bandas = detector_bandas(a, h)
    if not bandas:
        return None, "fallido", "sin bandas de contenido detectadas", None, None, 0

    motivo = []
    estado = "ok"

    # banda principal (la mas alta) = zona donde estan los uniformes
    principal = max(bandas, key=lambda b: b[1] - b[0])
    y0, y1 = principal

    # ── criterios para calificar la estructura ──
    if len(bandas) != 3:
        estado = "dudoso"
        motivo.append(f"{len(bandas)} bandas (se esperaban 3)")

    hay_cabecera = any(b[1] < y0 for b in bandas)
    hay_pie      = any(b[0] > y1 for b in bandas)
    if not hay_cabecera and not hay_pie:
        estado = "dudoso"
        motivo.append("sin cabecera ni pie (formato atipico)")

    seg = a[y0 : y1 + 1]
    frente, espalda, det = detectar_uniformes(seg, w)
    motivo.extend(det)

    if frente is None and espalda is None:
        bbox = (None, None, None, None)
        mask = (seg.mean(axis=2) < UMBRAL_FONDO)
        cols = np.where(mask.any(axis=0))[0]
        rows = np.where(mask.any(axis=1))[0]
        if len(cols) and len(rows):
            fx0, fx1, fy0, fy1 = (int(cols.min()), int(cols.max()),
                                  int(rows.min()), int(rows.max()))
            # solo se confia en el fallback si el contenido ocupa una
            # fraccion razonable de la banda central
            if (fx1 - fx0 + 1) >= 0.20 * w and (fy1 - fy0 + 1) >= 0.20 * (y1 - y0 + 1):
                bbox = (fx0, fx1, fy0, fy1)  # filas relativas a la banda
        recorte_fallback = True
        if bbox[0] is not None:
            x0, x1, fy0, fy1 = bbox
            estado = "dudoso"
            motivo.append("fallback: sin frente/espalda, recorte por contenido (revisar)")
        else:
            return None, "fallido", "no se detectaron uniformes en la zona central", None, None, len(bandas)
    else:
        recorte_fallback = False

    if frente is None:
        estado = "dudoso"
        motivo.append("frente no detectado (solo espalda)")
    if espalda is None and not recorte_fallback:
        # aceptable cuando el uniforme trasero es liso e indistinguible,
        # pero se deja constancia para revision
        estado = "dudoso"
        motivo.append("espalda no distinguible del fondo (revisar)")

    # ── recorte: desde el frente hasta el fin de la espalda ──
    if not recorte_fallback and frente is not None and espalda is not None:
        x0 = frente[0]
        x1 = espalda[1]
    elif recorte_fallback:
        pass  # (x0, x1, fy0, fy1) ya fueron fijados por el fallback
    elif frente is not None:
        x0, x1 = frente
    else:
        x0, x1 = espalda

    # ── ajuste fino al contenido util (quita marco/margenes) ──
    if recorte_fallback:
        y0_fb, y1_fb = fy0 + y0, fy1 + y0
        crop = im.crop((max(x0 - 2, 0), max(y0_fb - 2, 0),
                        min(x1 + 3, w), min(y1_fb + 3, h)))
    else:
        x0, x1, y0, y1 = ajustar_recorte(seg, x0, x1, y0, y1, margen=2)
        ancho = x1 - x0 + 1
        alto  = y1 - y0 + 1
        if ancho < 0.25 * w or alto < 0.20 * (y1 - y0 + 1) + 1:
            if estado == "ok":
                estado = "dudoso"
            motivo.append(f"recorte pequeno {ancho}x{alto}")
        crop = im.crop((x0, y0, x1 + 1, y1 + 1))

    # ── eliminar franjas oscuras residuales (bordes/marco) ──
    crop = recortar_franjas_oscuras(crop)

    # ── redimension conservando proporcion (sin ampliar de mas) ──
    cw, ch = crop.size
    lado = max(cw, ch)
    escala = 1.0
    if lado > CANVAS_SIZE:
        escala = CANVAS_SIZE / lado
    elif lado < CANVAS_SIZE / AMPLIACION_MAX:
        escala = min(AMPLIACION_MAX, CANVAS_SIZE / lado)
        if escala < 1.0:
            escala = 1.0
    nuevo = (max(1, int(round(cw * escala))), max(1, int(round(ch * escala))))
    if nuevo != (cw, ch):
        crop = crop.resize(nuevo, Image.LANCZOS)

    detalle = " | ".join(motivo) if motivo else "frente+espalda aislados correctamente"
    return crop, estado, detalle, frente, espalda, len(bandas)


# ─────────────────────────────────────────────
# VALIDACION HUMANA (muestra de 50)
# ─────────────────────────────────────────────

def generar_muestra_humana(ids, n=50):
    """
    Selecciona n IDs al azar y prepara data/revision_humana_{n}.csv (con
    columnas para clasificar) y un contact sheet (original | normalizada)
    para revision visual rapida. La clasificacion NO se rellena
    automaticamente: queda para el humano.
    """
    rev_csv = os.path.join(BASE_DIR, "data", f"revision_humana_{n}.csv")
    hoja = os.path.join(BASE_DIR, "data", f"revision_contact_sheet_{n}.png")

    rng = random.Random(42)
    muestra = rng.sample(sorted(ids), min(n, len(ids)))

    with open(rev_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "normalizada", "original",
                    "solo_frente_espalda", "sin_logo", "sin_marco",
                    "sin_cabecera_pie", "sin_cortes", "sin_deformacion",
                    "lienzo_ok", "clasificacion", "observacion"])
        for mid in muestra:
            w.writerow([mid,
                        os.path.join("images_normalized", mid),
                        os.path.join("images_final", mid),
                        "", "", "", "", "", "", "", "", ""])

    # contact sheet: 2 paneles (original | normalizada) por fila
    por_fila = 6
    filas = int(np.ceil(len(muestra) / por_fila))
    thumb = 200
    pad = 10
    panel = thumb * 2 + pad * 3
    hoja_im = Image.new("RGB",
                        (por_fila * panel + pad,
                         filas * thumb + pad * (filas + 1)),
                        (255, 255, 255))
    for i, mid in enumerate(muestra):
        r, c = divmod(i, por_fila)
        x = pad + c * (panel + pad)
        y = pad + r * (thumb + pad)
        for j, carpeta in enumerate(["images_final", "images_normalized"]):
            ruta = os.path.join(BASE_DIR, "data", carpeta, mid)
            if not os.path.exists(ruta):
                continue
            im = Image.open(ruta).convert("RGB")
            im.thumbnail((thumb, thumb))
            xx = x + j * (thumb + pad)
            hoja_im.paste(im, (xx, y + (thumb - im.size[1]) // 2))
    hoja_im.save(hoja)
    return rev_csv, hoja


# ─────────────────────────────────────────────
# PROCESAMIENTO PRINCIPAL
# ─────────────────────────────────────────────

def procesar(limite=None, canvas_size=CANVAS_SIZE, muestra=50):
    global CANVAS_SIZE
    CANVAS_SIZE = canvas_size
    os.makedirs(IMAGES_NORM, exist_ok=True)

    archivos = sorted(
        f for f in os.listdir(IMAGES_ORIGEN)
        if f.lower().endswith(EXTENSIONES)
    )
    if limite:
        archivos = archivos[:limite]
    total = len(archivos)

    print("=" * 60)
    print("SALA 1 / HITO 2 - NORMALIZACION DEL BANCO DE IMAGENES")
    print("=" * 60)
    print(f"Origen   : {IMAGES_ORIGEN}")
    print(f"Normaliz.: {IMAGES_NORM}")
    print(f"Imagenes : {total}")
    print(f"Lienzo   : lado mayor {CANVAS_SIZE} px (proporcion conservada)")
    print()

    t_inicio = time.perf_counter()
    resultados = []
    ok = dudosas = fallidas = 0
    recorte_ok = recorte_mal = 0
    con_frente = con_espalda = 0
    atipicas = []

    for idx, archivo in enumerate(archivos, start=1):
        origen = os.path.join(IMAGES_ORIGEN, archivo)
        im_out, estado, detalle, frente, espalda, n_bandas = normalizar_imagen(origen)

        if im_out is None:
            resultados.append([archivo, estado, detalle, "", "", "", ""])
            fallidas += 1
            recorte_mal += 1
            continue

        ext = os.path.splitext(archivo)[1].lower()
        base_id = os.path.splitext(archivo)[0]
        salida = os.path.join(IMAGES_NORM, base_id + ".jpg")
        im_out = im_out.convert("RGB")
        im_out.save(salida, "JPEG", quality=92)

        if frente is not None:
            con_frente += 1
        if espalda is not None:
            con_espalda += 1

        resultados.append([base_id + ".jpg", estado, detalle,
                           f"{im_out.size[0]}x{im_out.size[1]}", "ok-saved",
                           "si" if frente is not None else "no",
                           "si" if espalda is not None else "no"])
        if estado == "ok":
            ok += 1
            recorte_ok += 1
        else:
            dudosas += 1
            recorte_mal += 1
            if n_bandas != 3:
                atipicas.append(archivo)

        if idx % 100 == 0 or idx == total:
            print(f"  {idx:5d}/{total}  ok={ok}  dudoso={dudosas}  fallido={fallidas}")

    t_fin = time.perf_counter()
    tiempo_total = t_fin - t_inicio
    tiempo_prom = tiempo_total / max(1, total)

    # ── verificacion de integridad de salida ──
    todo_en_disco = sorted(os.listdir(IMAGES_NORM))
    salidas_jpg = [f for f in todo_en_disco if f.lower().endswith(".jpg")]
    hay_otras_ext = any(f.lower().endswith((".png", ".gif", ".jpeg")) for f in todo_en_disco)
    completo = len(salidas_jpg) == total and not hay_otras_ext
    integridad = "OK (100% .jpg)" if completo else (
        f"INCOMPLETO: {len(salidas_jpg)}/{total} .jpg, otras ext: {hay_otras_ext}")

    # ── guardar detalle CSV ──
    with open(DETALLE_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "estado", "motivo", "dimensiones_normalizada",
                    "guardada", "frente_detectado", "espalda_detectada"])
        w.writerows(resultados)

    # ── guardar reporte de texto ──
    with open(REPORTE_TXT, "w", encoding="utf-8") as f:
        f.write("REPORTE DE NORMALIZACION - SALA 1 / HITO 2\n")
        f.write("=" * 60 + "\n")
        f.write(f"Total encontradas       : {total}\n")
        f.write(f"Procesadas correctamente: {ok}\n")
        f.write(f"Fallidas                : {fallidas}\n")
        f.write(f"Dudosas (revisar)       : {dudosas}\n")
        f.write(f"Recorte correcto        : {recorte_ok}\n")
        f.write(f"Recorte incorrecto      : {recorte_mal}\n")
        f.write(f"Frente detectado        : {con_frente}\n")
        f.write(f"Espalda detectada       : {con_espalda}\n")
        f.write(f"Integridad de salida    : {integridad}\n")
        f.write(f"Tiempo total            : {tiempo_total:.2f} s\n")
        f.write(f"Tiempo promedio         : {tiempo_prom*1000:.1f} ms/imagen\n")
        f.write("=" * 60 + "\n")
        f.write("\nIMAGENES ATIPICAS (no siguen la estructura habitual):\n")
        if atipicas:
            for a_ in sorted(set(atipicas)):
                f.write(f"  {a_}\n")
        else:
            f.write("  (ninguna)\n")
        f.write("\nCASOS PARA REVISION HUMANA (dudosas + fallidas):\n")
        for archivo, estado, detalle, _, _, _, _ in resultados:
            if estado != "ok":
                f.write(f"  [{estado.upper()}] {archivo}  ->  {detalle}\n")

    # ── muestra para validacion humana ──
    ids_guardados = [r[0] for r in resultados if r[4] == "ok-saved"]
    if len(ids_guardados) >= muestra:
        rev_csv, hoja = generar_muestra_humana(ids_guardados, n=muestra)

    print()
    print("=" * 60)
    print(f"Total encontradas       : {total}")
    print(f"Procesadas correctamente: {ok}")
    print(f"Dudosas (revisar)       : {dudosas}")
    print(f"Fallidas                : {fallidas}")
    print(f"Recorte correcto        : {recorte_ok}")
    print(f"Recorte incorrecto      : {recorte_mal}")
    print(f"Frente detectado        : {con_frente}")
    print(f"Espalda detectada       : {con_espalda}")
    print(f"Integridad de salida    : {integridad}")
    print(f"Tiempo total            : {tiempo_total:.2f} s")
    print(f"Tiempo promedio         : {tiempo_prom*1000:.1f} ms/imagen")
    print("=" * 60)
    print(f"Reporte   : {REPORTE_TXT}")
    print(f"Detalle   : {DETALLE_CSV}")
    if len(ids_guardados) >= muestra:
        print(f"Revision  : {rev_csv}")
        print(f"Hoja      : {hoja}")

    return ok, dudosas, fallidas


def main():
    parser = argparse.ArgumentParser(description="Sala 1 / Hito 2 - Normalizacion del banco")
    parser.add_argument("--limite", type=int, default=None,
                        help="Procesar solo las primeras N imagenes (pruebas)")
    parser.add_argument("--canvas", type=int, default=CANVAS_SIZE,
                        help="Lado mayor del lienzo (default 700)")
    parser.add_argument("--muestra", type=int, default=50,
                        help="Tamano de la muestra para validacion humana (default 50)")
    parser.add_argument("--solo-muestra", action="store_true",
                        help="Solo regenerar la muestra humana (sin re-normalizar)")
    args = parser.parse_args()

    if args.solo_muestra:
        ids = [f for f in sorted(os.listdir(IMAGES_NORM))
               if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))]
        if len(ids) < args.muestra:
            sys.exit(f"No hay suficientes normalizadas ({len(ids)}) para muestra de {args.muestra}")
        rev_csv, hoja = generar_muestra_humana(ids, n=args.muestra)
        print("=" * 60)
        print(f"Muestra humana {args.muestra} (semilla 42)   -> {rev_csv}")
        print(f"Contact sheet                                 -> {hoja}")
        print("=" * 60)
        return

    procesar(limite=args.limite, canvas_size=args.canvas, muestra=args.muestra)


if __name__ == "__main__":
    main()
