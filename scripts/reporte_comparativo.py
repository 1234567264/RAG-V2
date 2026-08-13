# -*- coding: utf-8 -*-
"""
reporte_comparativo.py
----------------------
SALA 4 - Reporte comparativo consolidado (selección del modelo ganador).

Lee los archivos generados por las salas previas del flujo:

    data/evaluation_metrics.csv     precisión Top1/Top5 por modelo (y categoría)
    data/tiempos.csv                tiempos de generación (`generacion_*`) y de
                                    búsqueda (`*__clip|openclip|siglip`)
    data/revision_humana_50.csv     estructura de revisión cualitativa (Top 5)

Muestra en consola una tabla comparativa consolidada: precisión Top 1 y Top 5,
tiempos de generación de cada índice, tiempo promedio de búsqueda por consulta
y estado de la revisión humana. Al final declara el modelo ganador (mejor Top1,
desempate por Top5 y luego por tiempo de búsqueda).

Solo usa la biblioteca estándar (csv). Uso:

    python scripts/reporte_comparativo.py
"""

import csv
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
EVAL_METRICS_CSV = os.path.join(DATA_DIR, "evaluation_metrics.csv")
TIEMPOS_CSV = os.path.join(DATA_DIR, "tiempos.csv")
REVISION_CSV = os.path.join(DATA_DIR, "revision_humana_50.csv")

MODELO_CLAVE = {
    "clip": "CLIP",
    "openclip": "OpenCLIP",
    "siglip": "SigLIP",
}


def cargar_metricas():
    """Devuelve (globales, por_categoria) como listas de dicts."""
    if not os.path.exists(EVAL_METRICS_CSV):
        return None, None
    globales = []
    por_categoria = []
    with open(EVAL_METRICS_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["precision_top1"] = float(r.get("precision_top1") or 0)
            r["precision_top5"] = float(r.get("precision_top5") or 0)
            r["n_consultas"] = int(float(r.get("n_consultas") or 0))
            t = r.get("tiempo_busqueda_prom_ms")
            r["tiempo_busqueda_prom_ms"] = float(t) if str(t).strip() else None
            if r.get("categoria") == "global":
                globales.append(r)
            else:
                por_categoria.append(r)
    return globales, por_categoria


def cargar_tiempos():
    """Devuelve (tiempos_generacion, tiempos_busqueda)."""
    generacion = {}
    busqueda = {}
    if not os.path.exists(TIEMPOS_CSV):
        return generacion, busqueda
    with open(TIEMPOS_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            consulta = str(r.get("consulta", ""))
            try:
                segundos = float(r.get("tiempo_segundos") or 0)
            except ValueError:
                continue
            if consulta.startswith("generacion_"):
                generacion[consulta[len("generacion_"):]] = segundos
    for clave in MODELO_CLAVE:
        sufijo = f"__{clave}"
        acum = 0.0
        n = 0
        with open(TIEMPOS_CSV, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                consulta = str(r.get("consulta", ""))
                if not consulta.endswith(sufijo):
                    continue
                try:
                    acum += float(r.get("tiempo_segundos") or 0)
                except ValueError:
                    continue
                n += 1
        if n:
            busqueda[clave] = 1000 * acum / n
    return generacion, busqueda


def cargar_revision():
    """Estado de la revisión humana por modelo."""
    resumen = {}
    if not os.path.exists(REVISION_CSV):
        return resumen
    contadores = {clave: {"total": 0, "clasificadas": 0, "correctas": 0}
                  for clave in MODELO_CLAVE}
    with open(REVISION_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            clave = r.get("modelo", "")
            if clave not in contadores:
                continue
            contadores[clave]["total"] += 1
            clasif = str(r.get("clasificacion_humana") or "").strip()
            if clasif:
                contadores[clave]["clasificadas"] += 1
                if clasif == "Correcto":
                    contadores[clave]["correctas"] += 1
    return contadores


def imprimir_tabla(globales, tiempos_gen, tiempos_busq, revision):
    print("=" * 96)
    print("SALA 4 - REPORTE COMPARATIVO DE MODELOS Y EMBEDDINGS")
    print("=" * 96)

    if not globales:
        print("No existe data/evaluation_metrics.csv. Ejecutar primero:")
        print("  python scripts/evaluar_50_consultas.py")
        return None

    print("\nTabla consolidada por modelo:")
    print("-" * 96)
    print(f"{'Modelo':<10s}{'Top1%':>9s}{'Top5%':>9s}{'N':>5s}"
          f"{'Gen (s)':>10s}{'Búsq (ms)':>12s}{'Rev':>14s}")
    print("-" * 96)

    candidatos = []
    for r in globales:
        clave = r["modelo"]
        nombre = MODELO_CLAVE.get(clave, clave)
        gen = tiempos_gen.get(clave)
        busq = tiempos_busq.get(clave)
        rev = revision.get(clave)
        rev_txt = f"{rev['clasificadas']}/{rev['total']}" if rev else ""
        gen_txt = f"{gen:>9.1f}" if gen is not None else "     n/d"
        busq_txt = f"{busq:>11.1f}" if busq is not None else "         n/d"
        print(f"{nombre:<10s}{r['precision_top1']:>8.2f}%{r['precision_top5']:>8.2f}%"
              f"{r['n_consultas']:>5d}{gen_txt:>10s}{busq_txt:>12s}{rev_txt:>14s}")
        candidatos.append({
            "clave": clave, "nombre": nombre,
            "top1": r["precision_top1"], "top5": r["precision_top5"],
            "busq_ms": busq,
        })

    print("-" * 96)
    print("Top1% / Top5% = precisión sobre las 50 consultas. Gen = tiempo de\n"
          "generación del índice. Búsq = tiempo promedio por consulta.\n"
          "Rev = filas clasificadas/total en data/revision_humana_50.csv.")

    return candidatos


def imprimir_por_categoria(por_categoria):
    if not por_categoria:
        return
    categorias = sorted({r["categoria"] for r in por_categoria})
    print("\n" + "-" * 96)
    print("Precisión por categoría (Top1% / Top5%):")
    print("-" * 96)
    for categoria in categorias:
        fila = [r for r in por_categoria if r["categoria"] == categoria]
        partes = []
        for r in sorted(fila, key=lambda x: MODELO_CLAVE.get(x["modelo"], x["modelo"])):
            nombre = MODELO_CLAVE.get(r["modelo"], r["modelo"])
            partes.append(f"{nombre} {r['precision_top1']:.1f}/{r['precision_top5']:.1f}")
        print(f"  {categoria:<12s} " + "   |   ".join(partes))
    print("-" * 96)


def declarar_ganador(candidatos):
    if not candidatos:
        return
    ganador = max(
        candidatos,
        key=lambda c: (c["top1"], c["top5"],
                       -(c["busq_ms"] if c["busq_ms"] is not None else 1e18)),
    )
    print("\n" + "=" * 96)
    print(f"MODELO GANADOR: {ganador['nombre']}  "
          f"(Top1 {ganador['top1']:.2f}% / Top5 {ganador['top5']:.2f}%)")
    print("=" * 96)
    print("Criterio: mayor precisión Top 1; desempate por Top 5 y luego por\n"
          "tiempo promedio de búsqueda. Confirmar con la revisión humana de\n"
          "data/revision_humana_50.csv (utilidad cualitativa de los Top 2-5).")


def main():
    globales, por_categoria = cargar_metricas()
    tiempos_gen, tiempos_busq = cargar_tiempos()
    revision = cargar_revision()

    candidatos = imprimir_tabla(globales, tiempos_gen, tiempos_busq, revision)
    imprimir_por_categoria(por_categoria)
    declarar_ganador(candidatos)


if __name__ == "__main__":
    main()
