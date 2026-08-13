import json
import os
import re
from pathlib import Path
import shutil

# Raíz del proyecto (una carpeta arriba de utils/)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
HTML_DIR = os.path.join(DATA_DIR, "html")


def guardar_html(html):
    os.makedirs(HTML_DIR, exist_ok=True)
    with open(os.path.join(HTML_DIR, "pagina1.html"), "w", encoding="utf-8") as archivo:
        archivo.write(html)

    print("HTML guardado correctamente")

# ==========================

def guardar_productos(productos):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(
        os.path.join(DATA_DIR, "productos.json"),
        "w",
        encoding="utf-8"
    ) as archivo:
        json.dump(
            productos,
            archivo,
            indent=4,
            ensure_ascii=False
        )

    print("JSON guardado correctamente")

# ==========================

def leer_productos():

    ruta = Path(DATA_DIR) / "productos.json"

    if not ruta.exists():
        return []

    with open(
        ruta,
        "r",
        encoding="utf-8"
    ) as archivo:

        return json.load(archivo)
# ==========================

def limpiar_nombre(nombre):
    """
    Elimina caracteres inválidos para nombres de archivos.
    """

    return re.sub(
        r'[\\/:*?"<>|]',
        "-",
        nombre
    ).strip()


def obtener_extension(url):
    return Path(url).suffix

# ==========================

def crear_metadata_base():
    return {
        "items_por_pagina": None,
        "paginas": {}
    }


def guardar_metadata(metadata):

    carpeta = Path(DATA_DIR)

    carpeta.mkdir(exist_ok=True)

    archivo_metadata = carpeta / "metadata.json"

    with open(
        archivo_metadata,
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            metadata,
            archivo,
            indent=4,
            ensure_ascii=False
        )

# =========================

def leer_metadata():

    ruta = Path(DATA_DIR) / "metadata.json"


    if not ruta.exists():

        metadata = crear_metadata_base()

        guardar_metadata(metadata)

        return metadata


    with open(
        ruta,
        "r",
        encoding="utf-8"
    ) as archivo:

        metadata = json.load(archivo)


    # Compatibilidad con metadata antigua
    if "items_por_pagina" not in metadata:

        metadata["items_por_pagina"] = None


    if "paginas" not in metadata:

        metadata["paginas"] = {}


    return metadata

# ========================

def actualizar_metadata_pagina(pagina, cantidad):

    metadata = leer_metadata()


    metadata["paginas"][str(pagina)] = {
        "cantidad": cantidad
    }


    # Guardamos un valor de referencia
    # para cálculos rápidos
    if metadata["items_por_pagina"] is None:

        metadata["items_por_pagina"] = cantidad


    guardar_metadata(metadata)

    print(f"Metadata actualizada: página {pagina} ({cantidad} imágenes)")


# =========================

def limpiar_data():

    ruta = Path(DATA_DIR)


    if ruta.exists():

        shutil.rmtree(ruta)


    ruta.mkdir()

    print("Data limpiada correctamente")