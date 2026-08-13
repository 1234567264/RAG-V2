def limitar_productos(productos, limite):
    """
    Limita la cantidad de productos finales.

    Ejemplos:
    all -> devuelve todos
    100 -> devuelve primeros 100
    """

    if limite == "all":
        return productos


    limite = int(limite)

    return productos[:limite]