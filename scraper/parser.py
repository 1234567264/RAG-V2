from bs4 import BeautifulSoup
import re

from utils.helpers import (
    limpiar_nombre,
    obtener_extension
)


def obtener_id_producto(url):
    """
    Obtiene el ID único del producto desde la URL.
    """

    resultado = re.search(
        r'/products/([^/]+)/',
        url
    )

    if resultado:
        return resultado.group(1)

    return None



def extraer_productos(html, inicio=1, pagina=1):

    soup = BeautifulSoup(html, "lxml")

    imagenes = soup.find_all(
        "img",
        class_="productPreviewImage"
    )

    productos = []


    for indice, img in enumerate(imagenes, start=inicio):

        nombre = img.get("alt")

        url = img.get("src")


        id_producto = obtener_id_producto(url)


        extension = obtener_extension(url)


        archivo = (
            f"{indice}-"
            f"{limpiar_nombre(nombre)}"
            f"{extension}"
        )


        productos.append({

            "id": id_producto,
            "proveedor": "Designs Aimari",
            "pagina": pagina,
            "numero": indice,
            "nombre": nombre,
            "url": url,
            "archivo": archivo

        })


    return productos



def contar_imagenes(html):

    soup = BeautifulSoup(
        html,
        "lxml"
    )


    imagenes = soup.find_all(
        "img",
        class_="productPreviewImage"
    )


    return len(imagenes)