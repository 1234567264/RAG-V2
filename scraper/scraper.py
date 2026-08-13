import requests

from config.settings import URL_BASE


def obtener_html(pagina):

    url = URL_BASE.format(
        pagina=pagina
    )

    respuesta = requests.get(url)

    print("URL:", url)
    print("Código:", respuesta.status_code)

    respuesta.raise_for_status()

    return respuesta.text