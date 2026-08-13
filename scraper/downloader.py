import re
import time
import requests
from pathlib import Path

from utils.helpers import (
    leer_productos,
    IMAGES_DIR,
)


def limpiar_nombre_archivo(nombre):
    nombre = str(nombre).strip()

    # Eliminar saltos de línea, tabs y retornos de carro
    nombre = re.sub(r"[\r\n\t]+", " ", nombre)

    # Eliminar caracteres inválidos para Windows
    nombre = re.sub(r'[<>:"/\\|?*]', "", nombre)

    # Eliminar espacios repetidos
    nombre = re.sub(r"\s+", " ", nombre)

    return nombre


def descargar_una_imagen(url, ruta, intentos=5):

    for intento in range(1, intentos + 1):

        try:
            respuesta = requests.get(
                url,
                timeout=30
            )

            respuesta.raise_for_status()

            with open(ruta, "wb") as archivo:
                archivo.write(respuesta.content)

            return True

        except (requests.RequestException, OSError) as error:

            espera = 2

            if isinstance(error, requests.HTTPError):

                codigo = (
                    error.response.status_code
                    if error.response is not None
                    else 0
                )

                if codigo in (502, 503, 504, 429):
                    espera = 5

            print(
                f"[ERROR] Intento {intento}/{intentos} "
                f"→ {ruta.name}: {error}"
            )

            if intento < intentos:
                time.sleep(espera)

    return False


def descargar_imagenes():

    productos = leer_productos()

    ruta_imagenes = Path(IMAGES_DIR)

    ruta_imagenes.mkdir(
        parents=True,
        exist_ok=True
    )

    print(f"Verificando {len(productos)} imágenes...\n")

    descargadas = 0
    ya_existentes = 0
    fallidas = 0

    for producto in productos:

        nombre_archivo_original = producto["archivo"]

        nombre_archivo = limpiar_nombre_archivo(
            nombre_archivo_original
        )

        ruta_archivo = ruta_imagenes / nombre_archivo

        # Si ya existe, no volver a descargar
        if ruta_archivo.exists():
            print(f"[YA EXISTE] {nombre_archivo}")
            ya_existentes += 1
            continue

        # Descargar solamente las que faltan
        if descargar_una_imagen(
            producto["url"],
            ruta_archivo
        ):
            print(f"[OK] {nombre_archivo}")
            descargadas += 1

        else:
            print(f"[FALLÓ] {nombre_archivo}")
            fallidas += 1

    print("\nDescarga finalizada.")
    print(f"Ya existentes: {ya_existentes}")
    print(f"Descargadas: {descargadas}")
    print(f"Fallidas: {fallidas}")