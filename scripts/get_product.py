import csv
import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CSV_PATH = os.path.join(BASE_DIR, "data", "products.csv")

_CACHE = None  # evita releer el CSV en cada llamada


def _cargar_indice(csv_path: str = CSV_PATH):
    global _CACHE
    if _CACHE is None:
        with open(csv_path, "r", encoding="utf-8") as f:
            filas = list(csv.DictReader(f))
        _CACHE = {fila["id"]: fila for fila in filas}
    return _CACHE


def get_product_by_id(product_id: str, csv_path: str = CSV_PATH) -> dict | None:
    """
    Busca un producto por su ID en data/products.csv.

    Devuelve:
        {
            "id": "AIM-P001-001",
            "nombre": "Guadalcacin Blue",
            "imagen": "AIM-P001-001.jpg",
            "url": "https://...",
            "proveedor": "Designs Aimari"
        }
    o None si el ID no existe.
    """
    indice = _cargar_indice(csv_path)
    fila = indice.get(product_id)
    if fila is None:
        return None

    return {
        "id": fila["id"],
        "nombre": fila["nombre_original"],
        "imagen": fila["imagen"],
        "url": fila["url"],
        "proveedor": fila["proveedor"],
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python scripts/get_product.py <ID_PRODUCTO>")
        sys.exit(1)

    resultado = get_product_by_id(sys.argv[1])
    if resultado is None:
        print(f"No se encontró el producto con id '{sys.argv[1]}'")
    else:
        import json
        print(json.dumps(resultado, indent=4, ensure_ascii=False))