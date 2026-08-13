# -*- coding: utf-8 -*-
"""
reporte_evaluacion.py
-----------------------
Lee data/evaluacion.csv (generado al usar la app y guardar evaluaciones)
y arma la tabla final que pide la consigna:

    Consulta | Top 1 correcto | Top 5 útiles | Observación

Correr DESPUES de haber evaluado las 20 imagenes de prueba en la app:
    python reporte_evaluacion.py
"""

import os
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
EVAL_CSV = os.path.join(DATA_DIR, "evaluacion.csv")
REPORTE_XLSX = os.path.join(DATA_DIR, "reporte_evaluacion.xlsx")


def main():
    if not os.path.exists(EVAL_CSV):
        print(f"ERROR: no existe {EVAL_CSV} todavia.")
        print("Primero usa la app (streamlit run app.py) y guarda evaluaciones.")
        return

    df = pd.read_csv(EVAL_CSV)

    filas = []
    for consulta, grupo in df.groupby("consulta"):
        grupo = grupo.sort_values("rank")
        top1 = grupo[grupo["rank"] == 1]
        top1_correcto = "Sí" if not top1.empty and bool(top1.iloc[0]["correcto"]) else "No"
        top5_utiles = int(grupo["correcto"].sum())

        observaciones = grupo["observacion"].dropna().astype(str)
        observaciones = observaciones[observaciones.str.strip() != ""]
        observacion = observaciones.iloc[-1] if not observaciones.empty else ""

        filas.append({
            "Consulta": consulta,
            "Top 1 correcto": top1_correcto,
            "Top 5 útiles": f"{top5_utiles} de 5",
            "Observación": observacion,
        })

    reporte = pd.DataFrame(filas)
    reporte.to_excel(REPORTE_XLSX, index=False)

    print(reporte.to_string(index=False))
    print(f"\nGuardado en: {REPORTE_XLSX}")
    print(f"Total de consultas evaluadas: {len(reporte)} (la consigna pide 20)")


if __name__ == "__main__":
    main()
