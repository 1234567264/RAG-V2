import argparse
import sys

# Forzar salida UTF-8: en Windows la consola usa cp1252 y no puede imprimir
# caracteres como U+0301 (acento combinante) presentes en nombres de archivo,
# lo que mataba el scraper en el print de cada descarga.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from scraper.scraper import obtener_html
from scraper.downloader import descargar_imagenes
from storage.exporter import exportar_excel
from utils.limits import limitar_productos
from utils.update import fusionar_productos

from scraper.parser import (
    extraer_productos,
    contar_imagenes
)

from utils.pagination import (
    obtener_inicio_pagina,
    convertir_paginas,
    obtener_paginas_all,
    obtener_paginas_hasta_maximo,
    obtener_paginas_sin_metadata
)

from utils.helpers import (
    guardar_html,
    guardar_productos,
    actualizar_metadata_pagina,
    leer_productos,
    limpiar_data
)
# ===========================================================

def obtener_argumentos():

    parser = argparse.ArgumentParser(
        description="Aimari Web Scraper"
    )

    parser.add_argument(
        "--imagenes",
        default="all",
        help="Cantidad de imágenes: número o all"
    )

    parser.add_argument(
        "--paginas",
        default="1",
        help="Páginas a scrapear: ejemplo 1,2,3 o all"
    )

    parser.add_argument(
        "--modo",
        choices=["fresh", "update"],
        default="fresh",
        help="Modo de ejecución"
    )

    return parser.parse_args()



def main():
    args = obtener_argumentos()


    print("Configuración:")
    print("----------------")
    print(f"Imágenes: {args.imagenes}")
    print(f"Páginas: {args.paginas}")
    print(f"Modo: {args.modo}")
    print("----------------")

    if args.modo == "fresh":
        limpiar_data()

    if args.paginas == "all":
        print("\nDescubriendo páginas del catálogo...")
        paginas_solicitadas = obtener_paginas_all()
    else:
        paginas_solicitadas = convertir_paginas(args.paginas)

# =====================================
# 1) COMPLETAR METADATA FALTANTE
# =====================================

    paginas_necesarias = obtener_paginas_hasta_maximo(paginas_solicitadas)


    paginas_faltantes = obtener_paginas_sin_metadata(paginas_necesarias)


    if paginas_faltantes:

        print("\nCompletando metadata:")

        for pagina in paginas_faltantes:

            print(f"Obteniendo información página {pagina}")

            html = obtener_html(pagina)

            cantidad = contar_imagenes(html)

            actualizar_metadata_pagina(pagina,cantidad)


    else:
        print("\nMetadata completa")


    # =====================================
    # 2) SCRAPING REAL
    # =====================================

    productos_totales = []

    for pagina in paginas_solicitadas:

        print(f"\nProcesando página {pagina}")

        html = obtener_html(pagina)

        inicio = obtener_inicio_pagina(pagina)

        productos = extraer_productos(html,inicio=inicio,pagina=pagina)

        actualizar_metadata_pagina( pagina,len(productos))

        productos_totales.extend(productos)


    productos_scrapeados = limitar_productos(productos_totales, args.imagenes)

    if args.modo == "update":

        print("\nActualizando productos existentes...")

        productos_actuales = leer_productos()

        productos = fusionar_productos(productos_actuales,productos_scrapeados)

    else:

        productos = productos_scrapeados
    

    print(f"Productos encontrados: {len(productos_totales)}")
    print(f"Productos seleccionados: {len(productos)}")

    guardar_productos(productos)

    descargar_imagenes()

    exportar_excel()



if __name__ == "__main__":
    main()