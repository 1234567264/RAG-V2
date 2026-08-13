import json
import os
import re
import shutil
import csv
from PIL import Image  # pip install pillow

# Imagenes legitimas muy grandes (PNG de ~219M px en el banco) disparan el
# DecompressionBombError de Pillow al abrirse: se amplia el limite y los
# archivos excesivos se redimensionan antes de la validacion.
Image.MAX_IMAGE_PIXELS = None
MAX_PIXELES_POR_LADO = 4096  # lado mayor maximo tras el redimensionado
 
# ============================================================
# CONFIGURACIÓN — AJUSTA ESTO SEGÚN TU PROYECTO
# ============================================================
 
# Fuente: designsaimari.com
PROVEEDOR_NOMBRE = "Designs Aimari"
PROVEEDOR_PREFIJO = "AIM"
 
# Rutas base (raíz del proyecto WebScraping/data)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUTA_JSON = os.path.join(BASE_DIR, "data", "productos.json")
RUTA_IMAGENES_ORIGEN = os.path.join(BASE_DIR, "data", "images")
RUTA_IMAGENES_DESTINO = os.path.join(BASE_DIR, "data", "images_final")  # carpeta final a entregar
RUTA_CSV_SALIDA = os.path.join(BASE_DIR, "data", "products.csv")
 
# ============================================================
# 1. CARGA DE DATOS
# ============================================================
 
def cargar_productos():
    """
    Lee productos.json y devuelve una lista de diccionarios normalizados.
 
    Estructura real de tu productos.json (confirmada):
    { "id": str, "numero": int, "nombre": str, "url": str, "archivo": str }
 
    Tu JSON NO trae el campo "pagina" (número de página del scraping).
    Por defecto se asigna PAGINA_POR_DEFECTO a todos los registros.
    Si tu scraper sí paginó (ej. 20 productos por página), ajusta la
    función `calcular_pagina()` más abajo para que la calcule según
    "numero" en vez de usar un valor fijo.
    """
    with open(RUTA_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
 
    productos = []
    for item in data:
        productos.append({
            "id_scraper": item.get("id"),
            "numero": item.get("numero"),
            "nombre_original": item.get("nombre"),
            "imagen_original": item.get("archivo"),
            "url": item.get("url") or "",
            "pagina": calcular_pagina(item.get("numero")),
        })
    return productos
 
 
# Confirmado en data/metadata.json: 60 productos por página (3 páginas -> 180 productos)
PAGINA_POR_DEFECTO = 1
PRODUCTOS_POR_PAGINA = 60
 
 
def calcular_pagina(numero):
    if PRODUCTOS_POR_PAGINA and numero:
        return ((numero - 1) // PRODUCTOS_POR_PAGINA) + 1
    return PAGINA_POR_DEFECTO
 
 
# ============================================================
# 2. VALIDACIONES
# ============================================================

EXTENSIONES_PERMITIDAS = (".jpg", ".jpeg", ".png", ".gif")


def validar_imagen_abre(ruta_imagen):
    """Verifica que el archivo de imagen no esté corrupto y pueda abrirse."""
    try:
        with Image.open(ruta_imagen) as img:
            img.verify()
        return True
    except Exception:
        return False


def preparar_imagen(ruta_origen, ruta_destino, nombre_final):
    """
    Copia (o convierte) la imagen de origen al banco final siguiendo la
    nomenclatura canónica. Devuelve (imagen_final, error) donde imagen_final
    es el nombre de archivo usado en images_final o None si no se pudo.

    Reglas:
      - extension fuera de nomenclatura (ej. .webp) -> se convierte a .jpg;
      - imagen excesivamente grande -> se redimensiona (lado mayor <= 4096)
        para no reventar memoria en normalización/embeddings;
      - imagen ilegible -> error.
    """
    try:
        img = Image.open(ruta_origen)
        img.load()
    except Exception as e:
        return None, f"[CORRUPTA] No se pudo abrir la imagen '{os.path.basename(ruta_origen)}': {e}"

    ext = os.path.splitext(ruta_origen)[1].lower()

    if ext not in EXTENSIONES_PERMITIDAS:
        img = img.convert("RGB")
        nombre_final = os.path.splitext(nombre_final)[0] + ".jpg"
        img = redimensionar_si_es_nec(img)
        ruta_destino = os.path.join(os.path.dirname(ruta_destino), nombre_final)
        img.save(ruta_destino, "JPEG", quality=95)
        return nombre_final, None

    if max(img.size) > MAX_PIXELES_POR_LADO:
        img = redimensionar_si_es_nec(img)
        img.save(ruta_destino)
        return nombre_final, None

    shutil.copyfile(ruta_origen, ruta_destino)
    return nombre_final, None


def redimensionar_si_es_nec(img):
    """Reduce el lado mayor a MAX_PIXELES_POR_LADO conservando proporción."""
    lado = max(img.size)
    if lado <= MAX_PIXELES_POR_LADO:
        return img
    escala = MAX_PIXELES_POR_LADO / lado
    nuevo = (max(1, int(round(img.size[0] * escala))),
             max(1, int(round(img.size[1] * escala))))
    return img.resize(nuevo, Image.LANCZOS)
 
 
def nomenclatura_valida(nombre_archivo):
    """
    Verifica que el nombre siga el patrón PROVEEDOR-Pxxx-xxx.ext
    Ejemplo válido: BUS-P001-001.jpg
    """
    patron = rf"^{PROVEEDOR_PREFIJO}-P\d{{3}}-\d{{3,4}}\.(jpg|jpeg|png|gif)$"
    return re.match(patron, nombre_archivo, re.IGNORECASE) is not None
 
 
def ejecutar_validaciones(registros, errores):
    """
    Corre todas las verificaciones pedidas por la sala sobre la lista final
    de registros ya con su nuevo nombre de imagen asignado.

    Nota: las URLs repetidas NO son un error bloqueante: Designs Aimari
    reutiliza la misma URL de preview para productos distintos que tienen
    imágenes locales diferentes. Se reportan como aviso y cuentan para el
    informe (TRABAJO.md: "Cantidad de URLs repetidas").
    """
    nombres_vistos = set()
    urls_vistas = {}
    avisos = []

    for r in registros:
        # a) Que cada imagen tenga nombre
        if not r["imagen"]:
            errores.append(f"[SIN NOMBRE] Registro {r['id']} no tiene imagen asignada.")
            continue

        # b) Duplicados por nombre de imagen final (ID de archivo unico)
        if r["imagen"] in nombres_vistos:
            errores.append(f"[DUPLICADO] La imagen '{r['imagen']}' está repetida.")
        nombres_vistos.add(r["imagen"])

        # b2) URLs repetidas -> aviso (misma URL puede servir a 2 productos)
        if r["url"]:
            if r["url"] in urls_vistas:
                avisos.append(
                    f"[AVISO URL REPETIDA] '{r['url']}' usada por "
                    f"{urls_vistas[r['url']]} y {r['id']} (imágenes distintas)."
                )
            else:
                urls_vistas[r["url"]] = r["id"]
 
        # c) Nomenclatura
        if not nomenclatura_valida(r["imagen"]):
            errores.append(f"[NOMENCLATURA] '{r['imagen']}' no sigue el formato {PROVEEDOR_PREFIJO}-Pxxx-xxx.ext")
 
# d) El archivo debe existir físicamente y poder abrirse
        ruta_final = os.path.join(RUTA_IMAGENES_DESTINO, r["imagen"])
        if not os.path.exists(ruta_final):
            errores.append(f"[NO EXISTE] No se encontró el archivo físico: {ruta_final}")
        elif not validar_imagen_abre(ruta_final):
            errores.append(f"[CORRUPTA] El archivo no se pudo abrir: {ruta_final}")

    for a in avisos:
        print("  ⚠", a)
    if avisos:
        print(f"  ({len(avisos)} URL(s) repetida(s) entre productos distintos; "
              f"no son errores: cada producto conserva su propia imagen local.)")

    return errores
 
 
# ============================================================
# 3. CONSOLIDACIÓN (renombrado + generación de IDs)
# ============================================================
 
def indexar_imagenes_por_numero():
    """
    Recorre data/images y arma un índice { numero: ruta_completa }.
    Se usa el número al inicio del archivo (ej. '21-Bélgica Concept.jpg' -> 21)
    en vez del nombre completo, porque los nombres con tildes/ñ pueden
    llegar dañados según cómo se haya comprimido/movido la carpeta
    (ej. al hacer zip en Windows). El número es el único dato 100% estable.
    """
    indice = {}
    patron = re.compile(r"^(\d+)-")
    for archivo in os.listdir(RUTA_IMAGENES_ORIGEN):
        m = patron.match(archivo)
        if m:
            indice[int(m.group(1))] = os.path.join(RUTA_IMAGENES_ORIGEN, archivo)
    return indice
 
def consolidar():
    productos = cargar_productos()
    os.makedirs(RUTA_IMAGENES_DESTINO, exist_ok=True)

    # Índice { numero: ruta } como respaldo para los casos en que el nombre
    # del JSON trae espacios dobles/tildes dañadas y no existe tal cual en disco.
    indice_por_numero = indexar_imagenes_por_numero()

    registros = []
    errores = []

    for p in productos:
        numero = p.get("numero")

        origen = os.path.join(
            RUTA_IMAGENES_ORIGEN,
            p.get("imagen_original", "")
        )

        if not os.path.exists(origen):
            # Fallback: localizar la imagen por su número de producto
            origen = indice_por_numero.get(numero)

        if not origen:
            errores.append(
                f"[ARCHIVO FALTANTE] No se encontró imagen para el producto "
                f"#{numero} ('{p['nombre_original']}')."
            )
            continue

        ext = os.path.splitext(p["imagen_original"])[1].lower()

        # Posición del producto dentro de su página
        posicion_pagina = ((numero - 1) % PRODUCTOS_POR_PAGINA) + 1

        numero_str = f"{posicion_pagina:03d}"
        pagina_str = f"P{int(p['pagina']):03d}"

        id_registro = f"{PROVEEDOR_PREFIJO}-{pagina_str}-{numero_str}"
        nombre_final = f"{id_registro}{ext}"

        destino = os.path.join(
            RUTA_IMAGENES_DESTINO,
            nombre_final
        )

        # Copia/convertir con normas de nomenclatura y tamaño
        nombre_usado, error = preparar_imagen(origen, destino, nombre_final)
        if nombre_usado is None:
            errores.append(error)
            continue

        registros.append({
            "id": id_registro,
            "proveedor": PROVEEDOR_NOMBRE,
            "pagina": p["pagina"],
            "imagen": nombre_usado,
            "nombre_original": p["nombre_original"],
            "url": p["url"],
        })

    # Validaciones finales
    ejecutar_validaciones(registros, errores)

    # Escribir CSV
    with open(RUTA_CSV_SALIDA, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "proveedor",
                "pagina",
                "imagen",
                "nombre_original",
                "url"
            ]
        )

        writer.writeheader()
        writer.writerows(registros)

    # Limpieza: eliminar de images_final los archivos huérfanos de corridas
    # anteriores (esquemas viejos, IDs fuera de nomenclatura, etc.) para que la
    # carpeta contenga EXACTAMENTE el banco del CSV actual.
    nombres_validos = {r["imagen"] for r in registros}
    for f in os.listdir(RUTA_IMAGENES_DESTINO):
        if f not in nombres_validos:
            os.remove(os.path.join(RUTA_IMAGENES_DESTINO, f))

    # Reporte final
    print(f"\n✅ Procesados: {len(registros)} registros")
    print(f"✅ CSV generado en: {RUTA_CSV_SALIDA}")
    print(f"✅ Imágenes finales en: {RUTA_IMAGENES_DESTINO}")

    if errores:
        print(f"\n⚠️ Se encontraron {len(errores)} problema(s):")

        for e in errores:
            print("  -", e)
    else:
        print("\n🎉 Ninguna validación falló. Todo consistente.")

    return registros, errores
 
 
if __name__ == "__main__":
    consolidar()