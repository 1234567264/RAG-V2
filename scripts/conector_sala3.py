import os
import json
import pandas as pd


def cargar_productos_sala1(csv_path: str = None) -> pd.DataFrame:
    """
    Lee data/products.csv (entregado por Sala 1) y devuelve
    un DataFrame de pandas con las columnas requeridas.
    """
    if csv_path is None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        csv_path = os.path.join(base_dir, "data", "products.csv")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"No se encontró el archivo products.csv de Sala 1 en: {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8")

    columnas_requeridas = ["id", "nombre_original", "imagen", "url", "proveedor"]
    for col in columnas_requeridas:
        if col not in df.columns:
            df[col] = ""

    return df[columnas_requeridas]
