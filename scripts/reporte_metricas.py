# -*- coding: utf-8 -*-
"""
reporte_metricas.py (Sala 2, rama sala-2-v2)
---------------------------------------------
Lee data/evaluation.csv (generado desde la interfaz) y calcula:

    - Precision Top 1  (resultado en posicion 1 = Correcto)
    - Precision Top 5  (al menos 1 resultado Correcto o Util)
    - Falsos positivos (resultados marcados Incorrecto con score alto)
    - Falsos negativos (consultas sin ningun resultado relevante)
    - Tiempo promedio por consulta (desde data/tiempos.csv, si existe)

Tambien genera la tabla por consulta que pide la consigna:
    Consulta | Top 1 correcto | Top 5 utiles | Observacion

Uso:
    python reporte_metricas.py        # desde scripts/
"""

import os

import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
EVAL_CSV = os.path.join(DATA_DIR, "evaluation.csv")
TIEMPOS_CSV = os.path.join(DATA_DIR, "tiempos.csv")

UMBRAL_FALSO_POSITIVO = 0.70


def clasificacion_ok(etiqueta: str) -> bool:
    return etiqueta in ("Correcto", "Util_no_duplicado")


def clasificacion_correcta(etiqueta: str) -> bool:
    return etiqueta == "Correcto"


def main():
    if not os.path.exists(EVAL_CSV):
        print("ERROR: no existe data/evaluation.csv. Usa primero la interfaz.")
        return

    df = pd.read_csv(EVAL_CSV, encoding="utf-8")
    df["clasificacion_humana"] = df["clasificacion_humana"].astype(str).str.strip()
    df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0.0)

    filas = []
    for consulta, g in df.groupby("consulta"):
        g = g.sort_values("posicion")
        top1_correcto = any(
            (g["posicion"] == 1) & g["clasificacion_humana"].apply(clasificacion_correcta)
        )
        top5_util = any(g["clasificacion_humana"].apply(clasificacion_ok))
        obs = g["observacion"].dropna().astype(str)
        obs = obs[obs.str.strip() != ""]
        filas.append({
            "Consulta": consulta,
            "Top 1 correcto": "Si" if top1_correcto else "No",
            "Top 5 utiles": "Si" if top5_util else "No",
            "Observacion": obs.iloc[-1] if not obs.empty else "",
        })

    resumen = pd.DataFrame(filas)

    n_consultas = len(resumen)
    top1 = (resumen["Top 1 correcto"] == "Si").sum()
    top5 = (resumen["Top 5 utiles"] == "Si").sum()

    falsos_positivos = df[
        (df["clasificacion_humana"] == "Incorrecto") & (df["score"] >= UMBRAL_FALSO_POSITIVO)
    ]
    falsos_negativos = resumen[resumen["Top 5 utiles"] == "No"]

    print("=" * 60)
    print("REPORTE DE EVALUACION - SALA 2")
    print("=" * 60)
    print(f"Consultas evaluadas: {n_consultas} (la consigna pide 20)")
    print(f"Precision Top 1 : {top1} de {n_consultas} ({top1 / n_consultas * 100:.1f}%)" if n_consultas else "Precision Top 1 : 0")
    print(f"Precision Top 5 : {top5} de {n_consultas} ({top5 / n_consultas * 100:.1f}%)" if n_consultas else "Precision Top 5 : 0")
    print(f"Falsos positivos (Incorrecto con score >= {UMBRAL_FALSO_POSITIVO}): {len(falsos_positivos)}")
    print(f"Falsos negativos (consultas sin resultados relevantes): {len(falsos_negativos)}")

    if os.path.exists(TIEMPOS_CSV):
        tiempos = pd.read_csv(TIEMPOS_CSV, encoding="utf-8")
        tiempos["tiempo_segundos"] = pd.to_numeric(tiempos["tiempo_segundos"], errors="coerce")
        print(f"Tiempo promedio por consulta: {tiempos['tiempo_segundos'].mean():.3f} s "
              f"(min {tiempos['tiempo_segundos'].min():.3f} / max {tiempos['tiempo_segundos'].max():.3f})")
    else:
        print("Tiempo promedio por consulta: no disponible (falta data/tiempos.csv)")

    print()
    print(resumen.to_string(index=False))
    if not falsos_positivos.empty:
        print("\nDetalle falsos positivos:")
        print(falsos_positivos[["consulta", "resultado_id", "posicion", "score"]].to_string(index=False))
    if not falsos_negativos.empty:
        print("\nConsultas con falsos negativos:")
        print(falsos_negativos[["Consulta", "Observacion"]].to_string(index=False))

    resumen.to_excel(os.path.join(DATA_DIR, "reporte_evaluacion.xlsx"), index=False)
    print(f"\nGuardado: data/reporte_evaluacion.xlsx")


if __name__ == "__main__":
    main()
