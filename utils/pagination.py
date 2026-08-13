from utils.helpers import leer_metadata


import math
import re

from bs4 import BeautifulSoup

from scraper.parser import contar_imagenes
from scraper.scraper import obtener_html
from utils.helpers import leer_metadata


def convertir_paginas(valor):
    """
    Convierte el argumento --paginas en una lista de páginas.

    Ejemplos:
    "25"      -> [1,2,3,...,25]
    "1,3,5"   -> [1,3,5]
    "2-10"    -> [2,3,4,5,6,7,8,9,10]

    El valor "all" NO se maneja aquí: se resuelve en main.py con
    obtener_paginas_all(), que descubre el total del catálogo desde el sitio.
    """

    paginas = set()

    partes = valor.split(",")

    for parte in partes:

        parte = parte.strip()

        # Caso rango: 2-10
        if "-" in parte:

            inicio, fin = parte.split("-")

            inicio = int(inicio)
            fin = int(fin)

            paginas.update(
                range(inicio, fin + 1)
            )

        # Caso número: 25
        else:

            numero = int(parte)

            # Un número significa desde 1 hasta ese número
            paginas.update(
                range(1, numero + 1)
            )


    return sorted(paginas)


def total_productos_desde_html(html):
    """
    Extrae el total de productos del catálogo desde el resumen de paginación
    de cualquier página ("Mostrando 1-60 de 15282"). Devuelve None si no lo
    encuentra.
    """

    soup = BeautifulSoup(html, "lxml")

    resumen = soup.select_one(".catalogPaginationSummary")

    if resumen is None:
        return None

    match = re.search(
        r"de\s+(\d+)",
        resumen.get_text(" ", strip=True)
    )

    if not match:
        return None

    return int(match.group(1))


def obtener_paginas_all():
    """
    Resuelve "--paginas all": descubre la cantidad real de páginas del
    catálogo pidiendo la página 1 y leyendo el total de productos del
    resumen de paginación, dividido entre los ítems reales por página.
    """

    html = obtener_html(1)

    total = total_productos_desde_html(html)

    if total is None:
        raise Exception(
            "No se pudo determinar el total de productos: "
            "no se encontró el resumen de paginación en la página 1"
        )

    por_pagina = contar_imagenes(html)

    if not por_pagina:
        metadata = leer_metadata()
        por_pagina = metadata.get("items_por_pagina") or 60

    paginas = math.ceil(total / por_pagina)

    print(f"Catálogo descubierto: {total} productos, "
          f"{por_pagina} por página → {paginas} páginas")

    return list(range(1, paginas + 1))



def obtener_inicio_pagina(pagina):
    """
    Calcula el número global inicial del producto
    usando metadata real.

    Ejemplo:
    página 3:
    página 1 = 60
    página 2 = 60

    inicio = 121
    """

    metadata = leer_metadata()

    paginas_metadata = metadata["paginas"]

    total = 0


    for numero_pagina in range(1, pagina):

        datos = paginas_metadata.get(
            str(numero_pagina)
        )

        if datos is None:
            raise Exception(
                f"Falta metadata de página {numero_pagina}"
            )


        total += datos["cantidad"]


    return total + 1



def obtener_paginas_faltantes(paginas):
    """
    Revisa qué páginas no existen todavía
    en metadata.
    """

    metadata = leer_metadata()

    paginas_existentes = metadata["paginas"]

    faltantes = []


    for pagina in paginas:

        if str(pagina) not in paginas_existentes:

            faltantes.append(pagina)


    return faltantes



def obtener_maxima_pagina(paginas):
    return max(paginas)

# =============================
def obtener_paginas_hasta_maximo(paginas):

    """
    Devuelve todas las páginas necesarias
    desde 1 hasta la mayor solicitada.

    Ejemplo:

    [25]
    retorna:
    [1,2,3,...25]

    [2,5]
    retorna:
    [1,2,3,4,5]
    """

    maxima = max(paginas)

    return list(range(1, maxima + 1))

# ============================
def obtener_paginas_sin_metadata(paginas):
    metadata = leer_metadata()
    existentes = metadata["paginas"]
    faltantes = []

    for pagina in paginas:

        if str(pagina) not in existentes:

            faltantes.append(pagina)
            
    return faltantes