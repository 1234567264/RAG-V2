def fusionar_productos(
    productos_antiguos,
    productos_nuevos
):

    productos = {}

    # cargar antiguos
    for producto in productos_antiguos:

        productos[producto["id"]] = producto

    # actualizar/agregar nuevos
    for producto in productos_nuevos:

        productos[producto["id"]] = producto


    return list(productos.values())