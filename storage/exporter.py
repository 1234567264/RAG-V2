from pathlib import Path

from openpyxl import Workbook
from openpyxl.drawing.image import Image

from utils.helpers import leer_productos, IMAGES_DIR, DATA_DIR


def exportar_excel():

    productos = leer_productos()

    workbook = Workbook()

    hoja = workbook.active
    hoja.title = "Productos"

    hoja["A1"] = "N"
    hoja["B1"] = "Producto"
    hoja["C1"] = "Imagen"

    fila = 2

    for producto in productos:

        hoja[f"A{fila}"] = producto["numero"]
        hoja[f"B{fila}"] = producto["nombre"]

        ruta_imagen = Path(
            IMAGES_DIR
        ) / producto["archivo"]

        if ruta_imagen.exists():

            imagen = Image(str(ruta_imagen))

            imagen.width = 100
            imagen.height = 100

            hoja.add_image(
                imagen,
                f"C{fila}"
            )

        hoja.row_dimensions[fila].height = 80

        fila += 1

    hoja.column_dimensions["A"].width = 10
    hoja.column_dimensions["B"].width = 40
    hoja.column_dimensions["C"].width = 20

    workbook.save(
        Path(DATA_DIR) / "productos.xlsx"
    )

    print("Excel generado correctamente")