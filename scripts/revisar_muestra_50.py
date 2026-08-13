# -*- coding: utf-8 -*-
"""
revisar_muestra_50.py  -  Sala 1 / Hito 2-3, Actividad 5
------------------------------------------------------
Revision de las N imagenes normalizadas seleccionadas al azar
(data/revision_humana_{N}.csv, semilla 42, N=50 en el Hito 2 y
N=100 en el Hito 3).

Aplicacion de criterios OBJETIVOS y medibles sobre cada par
(original | normalizada) para completar las columnas de clasificacion:

  solo_frente_espalda : el lienzo contiene solo el uniforme (frente + espalda)
  sin_logo            : no queda logo/bloque ajeno separado a la izquierda
  sin_marco           : no quedan bordes/franjas oscuras en el borde
  sin_cabecera_pie    : no queda banda de cabecera/pie (URL) en el recorte
  sin_cortes          : se conservaron ambos bloques (frente y espalda)
  sin_deformacion     : la proporcion del recorte se conservo (escala uniforme)
  lienzo_ok           : lienzo uniforme (lado mayor 700 px) con contenido util
  clasificacion       : correcta | dudosa | incorrecta

Metodo: analisis de pixeles (brillo/densidad) sobre la imagen normalizada y
cruza con el estado reportado en data/detalle_normalizacion.csv. Para el
visto bueno visual definitivo queda la hoja de contacto
(data/revision_contact_sheet_{N}.png) y el CSV con clasificacion confirmada.

Uso:
    python scripts/revisar_muestra_50.py             # N=50 (Hito 2)
    python scripts/revisar_muestra_50.py --n 100     # N=100 (Hito 3)
"""

import csv
import os
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")

BASE_DIR    = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NORM_DIR    = os.path.join(BASE_DIR, "data", "images_normalized")
DETALLE     = os.path.join(BASE_DIR, "data", "detalle_normalizacion.csv")

CANVAS      = 700
CANVAS_MIN  = 350   # lado mayor minimo: no se amplia mas de 2x
UMBRAL      = 245   # brillo menor a esto => contenido
BANDA       = 0.80  # densidad de fila para considerar banda continua
BANDA_BRIL  = 170   # brillo medio de fila para considerar banda oscura


def abrir_rgb(ruta):
    from PIL import Image
    im = Image.open(ruta).convert("RGB")
    return np.asarray(im, dtype=np.float32)


def bandas_residuales(a, zona_frac=0.15):
    """
    Detecta bandas horizontales oscuras y densas (tipo cabecera/pie) en el
    borde superior/inferior de la imagen, separadas del contenido principal
    por una franja blanca. Devuelve ('sup'|'inf', ...) o None.
    """
    h, w, _ = a.shape
    br = a.mean(axis=2)
    densidad = (br < UMBRAL).mean(axis=1)
    filas_osc_dens = np.where((br.mean(axis=1) < BANDA_BRIL) & (densidad > BANDA))[0]
    if len(filas_osc_dens) == 0:
        return None
    zona = int(zona_frac * h)
    for lado, rango in (("sup", range(0, zona)), ("inf", range(h - zona, h))):
        filas = [y for y in filas_osc_dens if y in rango]
        if not filas:
            continue
        # separada del contenido por una franja clara?
        y0, y1 = min(filas), max(filas)
        if y1 - y0 + 1 < 3:
            continue
        if lado == "sup":
            claro = range(y1 + 1, min(h, y1 + 1 + max(1, int(0.03 * h))))
        else:
            claro = range(max(0, y0 - max(1, int(0.03 * h))), y0)
        if claro and all(br.mean(axis=1)[y] > 240 for y in claro):
            return (lado, y0, y1)
    return None


def logo_residual(a):
    """
    Detecta un bloque vertical separado y pegado al borde izquierdo
    (logo/icono que quedo en el recorte). Devuelve (x0, x1) o None.
    """
    h, w, _ = a.shape
    br = a.mean(axis=2)
    densidad = (br < UMBRAL).mean(axis=0)
    zona = int(0.12 * w)
    cols = np.where(densidad > BANDA)[0]
    if len(cols) == 0:
        return None
    cols_izq = [x for x in cols if x < zona]
    if not cols_izq:
        return None
    x0, x1 = min(cols_izq), max(cols_izq)
    if x1 - x0 + 1 < 3:
        return None
    # franja blanca que lo separa del contenido principal
    despues = range(x1 + 1, min(w, x1 + 1 + max(1, int(0.02 * w))))
    if despues and all(br.mean(axis=0)[x] > 240 for x in despues):
        return (x0, x1)
    return None


def marco_residual(a):
    """
    Borde oscuro que quedo separado del contenido por una franja clara
    (marco/banda residual de la tarjeta). Un recorte ajustado al contenido
    hace que la camiseta pueda tocar el borde; eso NO es marco.
    """
    h, w, _ = a.shape
    br = a.mean(axis=2)
    encontrados = []

    def franja_lateral(perfil, gap):
        t = 0
        while t < perfil.size and perfil[t] < 100:
            t += 1
        if t < 2:
            return False
        g = 0
        while t + g < perfil.size and perfil[t + g] > 220:
            g += 1
        return g >= max(2, int(0.01 * perfil.size))

    if franja_lateral(br.mean(axis=0), w):
        encontrados.append("izq")
    if franja_lateral(br.mean(axis=0)[::-1], w):
        encontrados.append("der")
    if franja_lateral(br.mean(axis=1), h):
        encontrados.append("sup")
    if franja_lateral(br.mean(axis=1)[::-1], h):
        encontrados.append("inf")
    return encontrados


def revisar_una(norm_path, estado_detalle):
    a = abrir_rgb(norm_path)
    h, w, _ = a.shape
    br = a.mean(axis=2)
    mask = br < UMBRAL

    cobertura = float(mask.mean())
    izq = float(mask[:, : max(2, int(0.30 * w))].mean())
    der = float(mask[:, int(0.70 * w):].mean())
    lado_mayor = max(w, h)
    lado_menor = min(w, h)

    band = bandas_residuales(a)
    logo = logo_residual(a)
    marco = marco_residual(a)

    checks = {}
    checks["solo_frente_espalda"] = "si" if (izq > 0.02 and der > 0.02 and
                                             0.05 <= cobertura <= 0.98) else "no"
    checks["sin_logo"] = "no" if logo else "si"
    checks["sin_marco"] = "no" if marco else "si"
    checks["sin_cabecera_pie"] = "no" if band else "si"
    checks["sin_cortes"] = "si" if (izq > 0.02 and der > 0.02) else "no"
    checks["sin_deformacion"] = "si" if CANVAS_MIN <= lado_mayor <= CANVAS else "no"
    checks["lienzo_ok"] = "si" if (CANVAS_MIN <= lado_mayor <= CANVAS and
                                   lado_menor >= 120 and cobertura >= 0.05) else "no"

    motivos = []
    if checks["solo_frente_espalda"] == "no":
        motivos.append("frente/espalda incompletos o lienzo vacio/lleno")
    if logo:
        motivos.append(f"logo residual x[{logo[0]}:{logo[1]}]")
    if marco:
        motivos.append(f"marco residual: {','.join(marco)}")
    if band:
        motivos.append(f"banda {band[0]} residual filas {band[1]}-{band[2]}")
    if checks["sin_cortes"] == "no":
        motivos.append("un lado del uniforme ausente")
    if checks["sin_deformacion"] == "no":
        motivos.append(f"lienzo {w}x{h} (lado mayor fuera de {CANVAS_MIN}-{CANVAS})")
    if checks["lienzo_ok"] == "no":
        motivos.append("lienzo no uniforme")

    if estado_detalle and estado_detalle != "ok":
        motivos.append(f"pipeline: {estado_detalle}")

    n_fallas = sum(1 for v in checks.values() if v == "no")
    if n_fallas == 0 and estado_detalle not in ("dudoso", "fallido"):
        clasif = "correcta"
    elif cobertura < 0.05 or (izq < 0.02 and der < 0.02):
        clasif = "incorrecta"
    else:
        clasif = "dudosa"

    obs = "; ".join(motivos) if motivos else "camiseta conservada correctamente"
    return checks, clasif, obs, cobertura, izq, der


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Revision objetiva de la muestra humana")
    parser.add_argument("--n", type=int, default=50,
                        help="Tamano de la muestra (default 50, Hito 3: 100)")
    parser.add_argument("--force", action="store_true",
                        help="Reevaluar tambien las filas ya clasificadas")
    args = parser.parse_args()

    n = args.n
    revision = os.path.join(BASE_DIR, "data", f"revision_humana_{n}.csv")
    informe  = os.path.join(BASE_DIR, "data", f"informe_revision_humana_{n}.txt")

    if not os.path.exists(revision):
        sys.exit(f"No existe {revision} "
                 f"(ejecutar normalizar_imagenes.py --solo-muestra --muestra {n})")

    estado_por_id = {}
    if os.path.exists(DETALLE):
        with open(DETALLE, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                estado_por_id[row["id"]] = row.get("estado", "")

    with open(revision, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))

    resumen = []
    total = 0
    for r in filas:
        if r["clasificacion"].strip() and not args.force:
            total += 1
            resumen.append(r)
            continue
        norm = os.path.join(NORM_DIR, r["id"])
        if not os.path.exists(norm):
            r["clasificacion"] = "incorrecta"
            r["observacion"] = "archivo normalizado no existe"
            total += 1
            resumen.append(r)
            continue
        checks, clasif, obs, cov, izq, der = revisar_una(norm, estado_por_id.get(r["id"], ""))
        r.update(checks)
        r["clasificacion"] = clasif
        r["observacion"] = obs
        total += 1
        resumen.append(r)

    with open(revision, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(resumen)

    ok = sum(1 for r in resumen if r["clasificacion"] == "correcta")
    dud = sum(1 for r in resumen if r["clasificacion"] == "dudosa")
    mal = sum(1 for r in resumen if r["clasificacion"] == "incorrecta")

    con_detalle = sum(1 for r in resumen if "pipeline:" in r["observacion"])

    with open(informe, "w", encoding="utf-8") as f:
        f.write(f"REVISION DE LAS {n} IMAGENES NORMALIZADAS - SALA 1 / HITO 2-3\n")
        f.write("=" * 60 + "\n")
        f.write(f"Revisadas                 : {total}\n")
        f.write(f"Correctas                 : {ok} ({100*ok/total:.0f}%)\n")
        f.write(f"Dudosas (revisar)         : {dud}\n")
        f.write(f"Incorrectas               : {mal}\n")
        f.write(f"Con aviso del pipeline    : {con_detalle}\n")
        f.write("\nDetalle por criterio (cuantas cumplen):\n")
        for campo in ("solo_frente_espalda", "sin_logo", "sin_marco",
                      "sin_cabecera_pie", "sin_cortes", "sin_deformacion",
                      "lienzo_ok"):
            c = sum(1 for r in resumen if r.get(campo) == "si")
            f.write(f"  {campo:22s}: {c}/{total}\n")
        f.write("\nCasos no 'correcta' (pendientes de revision visual):\n")
        for r in resumen:
            if r["clasificacion"] != "correcta":
                f.write(f"  [{r['clasificacion'].upper()}] {r['id']}  ->  {r['observacion']}\n")
        f.write("=" * 60 + "\n")
        f.write("\nMetodo: criterios objetivos de pixel (brillo/densidad) cruzados\n")
        f.write("con el estado del pipeline (detalle_normalizacion.csv). La hoja de\n")
        f.write("contacto revision_contact_sheet.png permite el visto bueno visual\n")
        f.write("final; la columna clasificacion se puede editar a mano.\n")

    print("=" * 60)
    print(f"Revisadas   : {total}")
    print(f"Correctas   : {ok} ({100*ok/total:.0f}%)")
    print(f"Dudosas     : {dud}")
    print(f"Incorrectas : {mal}")
    print(f"CSV    : {revision}")
    print(f"Informe: {informe}")


if __name__ == "__main__":
    main()
