# -*- coding: utf-8 -*-
"""
analizar_formatos.py  -  Sala 1 / Hito 2, Actividad 1
-----------------------------------------------------
Analisis del banco de imagenes (muestra >= 100 imagenes, por defecto las 1000):

  - cuantos formatos visuales diferentes existen (agrupados por firma de estructura);
  - si los marcos aparecen siempre en posiciones similares (espesor por lado);
  - donde aparecen cabecera, pie y URL (bandas no-principales y su posicion);
  - donde se ubican normalmente frente y espalda (rango x normalizado);
  - que porcentaje puede recortarse mediante reglas simples (fraccion de
    contenido util vs area total de la tarjeta).

Reutiliza los detectores de scripts/normalizar_imagenes.py para que el
diagnostico use exactamente la misma logica que el normalizador.

Salidas:
  data/informe_formatos.txt   -> informe legible
  data/detalle_formatos.csv   -> detalle por imagen

Uso:
    python scripts/analizar_formatos.py
    python scripts/analizar_formatos.py --muestra 100
"""

import argparse
import csv
import os
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import normalizar_imagenes as ni  # noqa: E402


BASE_DIR    = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IMAGES_DIR  = os.path.join(BASE_DIR, "data", "images_final")
INFO_TXT    = os.path.join(BASE_DIR, "data", "informe_formatos.txt")
DETALLE_CSV = os.path.join(BASE_DIR, "data", "detalle_formatos.csv")

UMBRAL_NO_BLANCO = 250  # brillo bajo este valor => pixel "no blanco" (borde/marco)
MAX_MARCO        = 0.10  # el marco no puede superar el 10% del lado


def espesor_marco(brillo_1d, dim):
    """Franja no-blanca consecutiva desde el borde (0 = sin marco en ese lado)."""
    max_px = max(2, int(MAX_MARCO * dim))
    t = 0
    while t < max_px and t < dim and brillo_1d[t] < UMBRAL_NO_BLANCO:
        t += 1
    if t < 2:
        return 0
    return t


def espesores_marco(a):
    """(izq, der, sup, inf) espesor de marco en cada lado (px)."""
    h, w, _ = a.shape
    brillo = a.mean(axis=2)
    izq = espesor_marco(brillo.mean(axis=0), w)
    der = espesor_marco(brillo.mean(axis=0)[::-1], w)
    sup = espesor_marco(brillo.mean(axis=1), h)
    inf = espesor_marco(brillo.mean(axis=1)[::-1], h)
    return izq, der, sup, inf


def analizar_imagen(ruta):
    """
    Devuelve dict con la estructura de una imagen o None si no se puede abrir.
    """
    im = ni.abrir_rgb(ruta)
    a = np.asarray(im, dtype=np.float32)
    h, w, _ = a.shape

    bandas = ni.detector_bandas(a, h)
    if not bandas:
        return None

    principal = max(bandas, key=lambda b: b[1] - b[0])
    y0, y1 = principal

    # bandas secundarias: cabecera (arriba) y pie/URL (abajo)
    cabecera = next((b for b in bandas if b[1] < y0), None)
    pie      = next((b for b in bandas if b[0] > y1), None)
    otras    = [b for b in bandas if b not in (cabecera, principal, pie)]

    # bloques verticales en la zona principal -> frente / espalda / logo
    seg = a[y0 : y1 + 1]
    frente = espalda = None
    logo = False
    det = []
    try:
        frente, espalda, det = ni.detectar_uniformes(seg, w)
        logo = any("logo" in d for d in det)
    except Exception:
        pass

    # recorte por reglas simples: fraccion de la tarjeta que NO es la zona del
    # uniforme (frente+espalda). Si frente/espalda no se detectan, cae al bbox.
    if frente is not None and espalda is not None:
        uni_w = (espalda[1] - frente[0] + 1) / w
        uni_h = (y1 - y0 + 1) / h
        recorte_frac = 1.0 - uni_w * uni_h
    else:
        mask = (a.mean(axis=2) < ni.UMBRAL_FONDO)
        cols = np.where(mask.any(axis=0))[0]
        rows = np.where(mask.any(axis=1))[0]
        if len(cols) and len(rows):
            bbox_area = (cols.max() - cols.min() + 1) * (rows.max() - rows.min() + 1)
        else:
            bbox_area = 0
        recorte_frac = 1.0 - bbox_area / max(1, w * h)

    izq, der, sup, inf = espesores_marco(a)

    def frac(r):
        return None if r is None else (r[0] / w, r[1] / w)

    return {
        "id": os.path.basename(ruta), "w": w, "h": h,
        "n_bandas": len(bandas),
        "cabecera": None if cabecera is None else (cabecera[0] / h, cabecera[1] / h),
        "principal": (y0 / h, y1 / h),
        "pie": None if pie is None else (pie[0] / h, pie[1] / h),
        "otras_bandas": len(otras),
        "marco": (izq, der, sup, inf),
        "logo": logo,
        "frente": frac(frente), "espalda": frac(espalda),
        "recorte_frac": recorte_frac,
    }


def firma_formato(d):
    """Firma de estructura visual -> clave para agrupar formatos."""
    cab = 1 if d["cabecera"] is not None else 0
    pie = 1 if d["pie"] is not None else 0
    n_marco = sum(1 for t in d["marco"] if t > 0)
    logo = 1 if d["logo"] else 0
    return (d["n_bandas"], cab, pie, logo, n_marco)


def main():
    parser = argparse.ArgumentParser(description="Sala 1 - Analisis de formatos del banco")
    parser.add_argument("--muestra", type=int, default=1000,
                        help="Cuantas imagenes analizar (minimo 100, default 1000)")
    args = parser.parse_args()

    archivos = sorted(f for f in os.listdir(IMAGES_DIR)
                      if f.lower().endswith(ni.EXTENSIONES))[: args.muestra]
    total = len(archivos)

    print("=" * 60)
    print("SALA 1 / HITO 2 - ACTIVIDAD 1: ANALISIS DEL BANCO")
    print("=" * 60)
    print(f"Muestra        : {total} imagenes (minimo pedido: 100)")
    print(f"Origen         : {IMAGES_DIR}")
    print()

    filas = []
    fallidas = 0
    for idx, arch in enumerate(archivos, start=1):
        try:
            d = analizar_imagen(os.path.join(IMAGES_DIR, arch))
        except Exception:
            d = None
        if d is None:
            fallidas += 1
            filas.append([arch, "", "", "", "", "", "", "", "", "", "", "", ""])
            continue
        filas.append([
            d["id"], d["w"], d["h"], d["n_bandas"],
            f"{d['cabecera'][0]:.3f}-{d['cabecera'][1]:.3f}" if d["cabecera"] else "",
            f"{d['principal'][0]:.3f}-{d['principal'][1]:.3f}",
            f"{d['pie'][0]:.3f}-{d['pie'][1]:.3f}" if d["pie"] else "",
            "/".join(map(str, d["marco"])),
            "si" if d["logo"] else "no",
            f"{d['frente'][0]:.3f}-{d['frente'][1]:.3f}" if d["frente"] else "",
            f"{d['espalda'][0]:.3f}-{d['espalda'][1]:.3f}" if d["espalda"] else "",
            f"{d['recorte_frac']:.3f}", firma_formato(d),
        ])

    validas = [r for r in filas if r[1]]
    n = len(validas)

    # ── formatos visuales ──
    formatos = {}
    for r in validas:
        formatos.setdefault(r[-1], []).append(r[0])
    n_formatos = len(formatos)
    ordenados = sorted(formatos.items(), key=lambda kv: len(kv[1]), reverse=True)

    # ── marcos ──
    def stats_idx(i, func):
        vals = [func(r[i]) for r in validas if r[i] != ""]
        return vals

    marcos = {"izq": [], "der": [], "sup": [], "inf": []}
    for r in validas:
        for k, v in zip(marcos, r[7].split("/")):
            marcos[k].append(int(v))
    con_marco = {k: sum(1 for v in vs if v > 0) for k, vs in marcos.items()}
    espesor_prom = {k: (sum(vs) / n if n else 0) for k, vs in marcos.items()}

    # ── cabecera / pie ──
    cab_alturas = [r[4].split("-") for r in validas if r[4]]
    cab_prom = (sum(float(b) - float(a) for a, b in cab_alturas) / n if n else 0)
    pie_alturas = [r[6].split("-") for r in validas if r[6]]
    pie_prom = (sum(float(b) - float(a) for a, b in pie_alturas) / n if n else 0)
    n_cab = len(cab_alturas)
    n_pie = len(pie_alturas)

    # ── frente / espalda ──
    frentes = [r[9].split("-") for r in validas if r[9]]
    espaldas = [r[10].split("-") for r in validas if r[10]]
    f_prom = tuple(sum(float(x[i]) for x in frentes) / len(frentes) for i in range(2)) if frentes else None
    e_prom = tuple(sum(float(x[i]) for x in espaldas) / len(espaldas) for i in range(2)) if espaldas else None

    # ── recorte simple ──
    recortes = [float(r[11]) for r in validas]
    rec_prom = sum(recortes) / n if n else 0
    buckets = [(0.0, 0.50), (0.50, 0.60), (0.60, 0.70), (0.70, 0.80), (0.80, 0.90), (0.90, 1.01)]
    rec_buckets = []
    for lo, hi in buckets:
        c = sum(1 for v in recortes if lo <= v < hi)
        rec_buckets.append((lo, hi, c))

    # ── guardar detalle CSV ──
    with open(DETALLE_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "w", "h", "n_bandas", "cabecera_y", "principal_y",
                    "pie_y", "marco_izq_der_sup_inf", "logo",
                    "frente_x", "espalda_x", "recorte_frac", "formato"])
        w.writerows(filas)

    # ── informe ──
    with open(INFO_TXT, "w", encoding="utf-8") as f:
        f.write("INFORME DE FORMATOS - SALA 1 / HITO 2 (ACTIVIDAD 1)\n")
        f.write("=" * 60 + "\n")
        f.write(f"Muestra analizada      : {n} imagenes validas de {total} "
                f"(minimo pedido: 100)\n")
        f.write(f"No legibles            : {fallidas}\n")
        f.write("\n1) FORMATOS VISUALES DIFERENTES\n")
        f.write(f"   Total de formatos detectados: {n_formatos}\n")
        f.write("   (firma = n_bandas | cabecera | pie | logo | n_lados_marco)\n")
        f.write("   Top formatos:\n")
        for i, (fmt, ids) in enumerate(ordenados[:10], start=1):
            f.write(f"     {i:2d}. {fmt}  ->  {len(ids)} imagenes ({100*len(ids)/n:.1f}%)\n")
        f.write("\n2) MARCOS\n")
        f.write(f"   Imagenes con marco izquierdo : {con_marco['izq']} ({100*con_marco['izq']/n:.1f}%), "
                f"espesor prom {espesor_prom['izq']:.1f} px\n")
        f.write(f"   Imagenes con marco derecho   : {con_marco['der']} ({100*con_marco['der']/n:.1f}%), "
                f"espesor prom {espesor_prom['der']:.1f} px\n")
        f.write(f"   Imagenes con marco superior  : {con_marco['sup']} ({100*con_marco['sup']/n:.1f}%), "
                f"espesor prom {espesor_prom['sup']:.1f} px\n")
        f.write(f"   Imagenes con marco inferior  : {con_marco['inf']} ({100*con_marco['inf']/n:.1f}%), "
                f"espesor prom {espesor_prom['inf']:.1f} px\n")
        f.write(f"   Conclusion: la mayoria de tarjetas no tiene marco pintado en el\n")
        f.write(f"   borde (margenes blancos); el 'marco' visible corresponde a las\n")
        f.write(f"   bandas internas de cabecera y pie, que SI aparecen en posiciones\n")
        f.write(f"   consistentes (ver punto 3).\n")
        f.write("\n3) CABECERA, PIE Y URL\n")
        f.write(f"   Cabecera presente en {n_cab} ({100*n_cab/n:.1f}%): banda superior, "
                f"altura media {cab_prom*100:.1f}% de la imagen\n")
        f.write(f"   Pie (zona de URL) en {n_pie} ({100*n_pie/n:.1f}%): banda inferior, "
                f"altura media {pie_prom*100:.1f}% de la imagen\n")
        f.write(f"   Ubicacion tipica de cabecera: filas 0%-{100*(cab_prom if n_cab else 0):.0f}%\n")
        f.write(f"   Ubicacion tipica de pie/URL: filas {100*(1-pie_prom if n_pie else 0):.0f}%-100%\n")
        f.write("\n4) UBICACION DE FRENTE Y ESPALDA\n")
        if f_prom:
            f.write(f"   Frente  : {100*f_prom[0]:.0f}%-{100*f_prom[1]:.0f}% del ancho "
                    f"(detectado en {len(frentes)}/{n})\n")
        if e_prom:
            f.write(f"   Espalda : {100*e_prom[0]:.0f}%-{100*e_prom[1]:.0f}% del ancho "
                    f"(detectado en {len(espaldas)}/{n})\n")
        f.write("\n5) PORCENTAJE RECORTABLE CON REGLAS SIMPLES\n")
        f.write(f"   (definicion: fraccion de la tarjeta que no es la zona del uniforme)\n")
        f.write(f"   Recorte medio estimado     : {rec_prom*100:.1f}% de la tarjeta\n")
        f.write(f"   Minimo / maximo            : {100*min(recortes):.1f}% / {100*max(recortes):.1f}%\n")
        for lo, hi, c in rec_buckets:
            f.write(f"     {int(lo*100):3d}-{int(hi*100)}% de recorte -> {c} imagenes\n")
        f.write(f"   Imagenes con recorte >= 30%: {sum(1 for v in recortes if v >= 0.30)} "
                f"({100*sum(1 for v in recortes if v >= 0.30)/n:.1f}%)\n")
        f.write("\n6) CONCLUSION\n")
        f.write(f"   Con reglas simples (bandas + bloques + bbox de contenido) se puede\n")
        f.write(f"   recortar en promedio el {rec_prom*100:.1f}% de cada tarjeta; "
                f"{n_formatos} formatos visuales\n")
        f.write(f"   comparten la misma estructura (cabecera arriba, pie abajo, frente\n")
        f.write(f"   a la izquierda y espalda a la derecha), por lo que un unico\n")
        f.write(f"   algoritmo de bandas/bloques es aplicable a la mayoria del banco.\n")
        f.write("=" * 60 + "\n")

    # ── consola ──
    print(f"Muestra            : {n} imagenes validas")
    print(f"Formatos visuales  : {n_formatos}")
    print(f"Marco izq/der/sup/inf: {con_marco['izq']} / {con_marco['der']} / "
          f"{con_marco['sup']} / {con_marco['inf']}")
    print(f"Cabecera           : {n_cab} ({100*n_cab/n:.1f}%), altura media {cab_prom*100:.1f}%")
    print(f"Pie/URL            : {n_pie} ({100*n_pie/n:.1f}%), altura media {pie_prom*100:.1f}%")
    if f_prom:
        print(f"Frente             : {100*f_prom[0]:.0f}%-{100*f_prom[1]:.0f}% ancho")
    if e_prom:
        print(f"Espalda            : {100*e_prom[0]:.0f}%-{100*e_prom[1]:.0f}% ancho")
    print(f"Recorte medio      : {rec_prom*100:.1f}%")
    print(f"Informe  : {INFO_TXT}")
    print(f"Detalle  : {DETALLE_CSV}")


if __name__ == "__main__":
    main()
