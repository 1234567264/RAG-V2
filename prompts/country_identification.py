# -*- coding: utf-8 -*-
"""
country_identification.py - Prompt de identificación por país/equipo
-------------------------------------------------------------------
Sistema de prompts para identificar camisetas deportivas por país,
equipo, colores y características visuales. Diseñado para funcionar
con el motor de búsqueda visual Fusion (CLIP + OpenCLIP + SigLIP).

Uso:
    from prompts.country_identification import (
        IDENTIFICATION_PROMPT,
        IDENTIFICATION_SYSTEM_PROMPT,
        PAISES_FUTBOL,
        identificar_pais_equipo,
    )

    # Para enviar a un LLM (si se integra):
    prompt = IDENTIFICATION_PROMPT.format(
        colores_detectados="azul y blanco",
        patron_detectado="rayas horizontales",
    )
"""

# =============================================================================
# PROMPT PRINCIPAL - Identificación de camiseta por país/equipo
# =============================================================================

IDENTIFICATION_SYSTEM_PROMPT = """Eres un experto en camisetas deportivas de fútbol mundial.

Tu tarea es analizar una imagen de camiseta y determinar:
1. **País** al que pertenece (o al que representa)
2. **Equipo** específico (selección, club, etc.)
3. **Colores principales y secundarios** exactos
4. **Patrón o diseño** (rayas, franjas, degradados, sólido, etc.)
5. **Elementos distintivos** (escudo, marca, dorsales, bandera, etc.)
6. **Época/versión** si es identificable (local, visitante, alternativa)

Responde SIEMPRE en este formato JSON:
{
  "pais": "nombre del país",
  "equipo": "nombre del equipo o selección",
  "colores_principales": ["color1", "color2"],
  "colores_secundarios": ["color3"],
  "patron": "descripción del patrón/diseño",
  "elementos_distintivos": ["elemento1", "elemento2"],
  "epoca": "local/visitante/alternativa/desconocida",
  "confianza": 0.0-1.0,
  "descripcion_breve": "Una línea describiendo la camiseta"
}

Reglas:
- Si no puedes determinar el país,ponde "desconocido" pero describe los colores fielmente.
- Si es una camiseta genérica sin país específico, responde "genérica" en país.
- Los colores deben ser específicos: "azul marino" no solo "azul".
- El patrón debe ser descriptivo: "rayas horizontales azules y blancas" no solo "rayas".
- La confianza refleja qué tan seguro estás de la identificación."""

IDENTIFICATION_PROMPT = """Analiza esta imagen de camiseta deportiva y determina su país, equipo, colores y características.

{contexto_adicional}

Características visuales detectadas por el sistema:
- Colores dominantes: {colores_detectados}
- Patrón detectado: {patron_detectados}
- Estructura: {estructura_detectada}

Responde con el JSON especificado."""


# =============================================================================
# BASE DE DATOS DE PAÍSES Y EQUIPOS DE FÚTBOL
# =============================================================================

PAISES_FUTBOL = {
    "argentina": {
        "nombre_completo": "Argentina",
        "seleccion": "La Albiceleste",
        "colores": ["celeste", "blanco"],
        "colores_hex": ["75AADB", "FFFFFF"],
        "patron_tipico": "Rayas horizontales celestes y blancas",
        "elementos": ["AFA", "tres estrellas", "bandera argentina"],
        "equipos_famosos": [
            "Argentina (selección)",
            "River Plate",
            "Boca Juniors",
            "Racing Club",
            "Independiente",
            "San Lorenzo",
        ],
        "descripcion": "Rayas horizontales celestes y blancas, escudo AFA con estrellas",
    },
    "brasil": {
        "nombre_completo": "Brasil",
        "seleccion": "La Canarinha",
        "colores": ["amarillo", "verde", "azul"],
        "colores_hex": ["FFDF00", "009739", "002776"],
        "patron_tipico": "Amarillo con detalles verdes y azules",
        "elementos": ["CBF", "cinco estrellas", "bandera brasileña"],
        "equipos_famosos": [
            "Brasil (selección)",
            "Flamengo",
            "São Paulo",
            "Palmeiras",
            "Santos",
            "Corinthians",
        ],
        "descripcion": "Amarillo dominante con franja verde en el pecho",
    },
    "españa": {
        "nombre_completo": "España",
        "seleccion": "La Roja",
        "colores": ["rojo", "amarillo"],
        "colores_hex": ["AA151F", "FABD00"],
        "patron_tipico": "Rojo con detalles amarillos",
        "elementos": ["RFEF", "bandera española"],
        "equipos_famosos": [
            "España (selección)",
            "Real Madrid",
            "FC Barcelona",
            "Atlético Madrid",
            "Sevilla FC",
        ],
        "descripcion": "Rojo dominante con detalles amarillos y escudo RFEF",
    },
    "alemania": {
        "nombre_completo": "Alemania",
        "seleccion": "Die Mannschaft",
        "colores": ["blanco", "negro", "rojo"],
        "colores_hex": ["FFFFFF", "000000", "DD0000"],
        "patron_tipico": "Blanco con detalles negros y rojos",
        "elementos": ["DFB", "cuatro estrellas", "bandera alemana"],
        "equipos_famosos": [
            "Alemania (selección)",
            "Bayern München",
            "Borussia Dortmund",
            "Bayer Leverkusen",
        ],
        "descripcion": "Blanco limpio con franja negra y detalles rojos",
    },
    "francia": {
        "nombre_completo": "Francia",
        "seleccion": "Les Bleus",
        "colores": ["azul", "blanco", "rojo"],
        "colores_hex": ["002395", "FFFFFF", "ED2939"],
        "patron_tipico": "Azul dominante con detalles blancos y rojos",
        "elementos": ["FFF", "dos estrellas", "bandera francesa"],
        "equipos_famosos": [
            "Francia (selección)",
            "Paris Saint-Germain",
            "Olympique Marsella",
            "Olympique Lyonnais",
        ],
        "descripcion": "Azul marino con detalles blancos y rojos",
    },
    "inglaterra": {
        "nombre_completo": "Inglaterra",
        "seleccion": "The Three Lions",
        "colores": ["blanco"],
        "colores_hex": ["FFFFFF"],
        "patron_tipico": "Blanco con detalles azules",
        "elementos": ["tres leones", "FA"],
        "equipos_famosos": [
            "Inglaterra (selección)",
            "Manchester United",
            "Liverpool FC",
            "Chelsea FC",
            "Arsenal FC",
            "Manchester City",
        ],
        "descripcion": "Blanco con escudo de tres leones y detalles azules",
    },
    "italia": {
        "nombre_completo": "Italia",
        "seleccion": "Gli Azzurri",
        "colores": ["azul"],
        "colores_hex": ["004B87"],
        "patron_tipico": "Azul celeste sólido",
        "elementos": ["FIGC", "cuatro estrellas", "escudo italiano"],
        "equipos_famosos": [
            "Italia (selección)",
            "Juventus",
            "AC Milan",
            "Inter Milan",
            "AS Roma",
            "SSC Napoli",
        ],
        "descripcion": "Azul celeste sólido con escudo FIGC",
    },
    "uruguay": {
        "nombre_completo": "Uruguay",
        "seleccion": "La Celeste",
        "colores": ["azul", "blanco"],
        "colores_hex": ["5BCBF4", "FFFFFF"],
        "patron_tipico": "Celeste con detalles blancos",
        "elementos": ["AUF", "cuatro estrellas", "bandera uruguaya"],
        "equipos_famosos": [
            "Uruguay (selección)",
            "Club Nacional de Football",
            "Club Atlético Peñarol",
        ],
        "descripcion": "Celeste con franjas blancas y escudo AUF",
    },
    "portugal": {
        "nombre_completo": "Portugal",
        "seleccion": "A Seleção",
        "colores": ["rojo", "verde"],
        "colores_hex": ["006600", "FF0000"],
        "patron_tipico": "Rojo con detalles verdes",
        "elementos": ["FPF", "bandera portuguesa"],
        "equipos_famosos": [
            "Portugal (selección)",
            "SL Benfica",
            "FC Porto",
            "Sporting CP",
        ],
        "descripcion": "Rojo con franja vertical verde y escudo FPF",
    },
    "colombia": {
        "nombre_completo": "Colombia",
        "seleccion": "Los Cafeteros",
        "colores": ["amarillo", "azul", "rojo"],
        "colores_hex": ["FCD116", "003893", "CE1126"],
        "patron_tipico": "Amarillo dominante con detalles azules y rojos",
        "elementos": ["FCF", "bandera colombiana"],
        "equipos_famosos": [
            "Colombia (selección)",
            "Millonarios FC",
            "Atlético Nacional",
            "América de Cali",
        ],
        "descripcion": "Amarillo con franja azul y detalles rojos",
    },
    "mexico": {
        "nombre_completo": "México",
        "seleccion": "El Tri",
        "colores": ["verde", "blanco", "rojo"],
        "colores_hex": ["006847", "FFFFFF", "CE1126"],
        "patron_tipico": "Verde dominante con detalles blancos y rojos",
        "elementos": ["FMF", "águila", "bandera mexicana"],
        "equipos_famosos": [
            "México (selección)",
            "Club América",
            "Cruz Azul",
            "Chivas de Guadalajara",
            "Pumas UNAM",
        ],
        "descripcion": "Verde con detalles blancos y rojos, escudo FMF",
    },
    "holanda": {
        "nombre_completo": "Países Bajos",
        "seleccion": "Oranje",
        "colores": ["naranja"],
        "colores_hex": ["FF6600"],
        "patron_tipico": "Naranja dominante",
        "elementos": ["KNVB", "bandera neerlandesa"],
        "equipos_famosos": [
            "Países Bajos (selección)",
            "Ajax",
            "PSV Eindhoven",
            "Feyenoord",
        ],
        "descripcion": "Naranja vibrante con escudo KNVB",
    },
    "japon": {
        "nombre_completo": "Japón",
        "seleccion": "Samurai Blue",
        "colores": ["azul", "blanco"],
        "colores_hex": ["00214F", "FFFFFF"],
        "patron_tipico": "Azul oscuro con detalles blancos",
        "elementos": ["JFA", "sol naciente"],
        "equipos_famosos": [
            "Japón (selección)",
            "Kashima Antlers",
            "Yokohama F. Marinos",
        ],
        "descripcion": "Azul marino con detalles blancos y sol naciente",
    },
    "corea_del_sur": {
        "nombre_completo": "Corea del Sur",
        "seleccion": "Taegeuk Warriors",
        "colores": ["rojo", "azul", "blanco"],
        "colores_hex": ["CD2E3A", "0047A0", "FFFFFF"],
        "patron_tipico": "Blanco con detalles rojos y azules",
        "elementos": ["KFA", "tigre", "bandera surcoreana"],
        "equipos_famosos": [
            "Corea del Sur (selección)",
            "Ulsan Hyundai",
            "Jeonbuk Hyundai Motors",
        ],
        "descripcion": "Blanco con patrón rojo y azul inspired en la bandera",
    },
    "nigeria": {
        "nombre_completo": "Nigeria",
        "seleccion": "Super Eagles",
        "colores": ["verde", "blanco"],
        "colores_hex": ["008751", "FFFFFF"],
        "patron_tipico": "Verde con detalles blancos",
        "elementos": ["NFF", "águila", "bandera nigeriana"],
        "equipos_famosos": [
            "Nigeria (selección)",
            "Enyimba FC",
        ],
        "descripcion": "Verde con patrón geométrico y detalles blancos",
    },
    "senegal": {
        "nombre_completo": "Senegal",
        "seleccion": "Les Lions de la Téranga",
        "colores": ["verde", "amarillo", "rojo"],
        "colores_hex": ["00853F", "FDEF42", "E31B23"],
        "patron_tipico": "Verde con detalles amarillos y rojos",
        "elementos": ["FSF", "león", "bandera senegalesa"],
        "equipos_famosos": [
            "Senegal (selección)",
        ],
        "descripcion": "Verde con estrella amarilla y detalles rojos",
    },
}


# =============================================================================
# DICCIONARIO INVERSO: COLOR -> PAÍSES
# =============================================================================

COLOR_A_PAISES = {}
for pais, info in PAISES_FUTBOL.items():
    for color in info["colores"]:
        if color not in COLOR_A_PAISES:
            COLOR_A_PAISES[color] = []
        COLOR_A_PAISES[color].append(pais)


# =============================================================================
# FUNCIÓN DE IDENTIFICACIÓN POR COLORES
# =============================================================================

def identificar_pais_equipo(colores_detectados: list[str], patron: str = "") -> list[dict]:
    """
    Dada una lista de colores detectados y un patrón opcional,
    devuelve los países/equipos más probables ordenados por relevancia.

    Args:
        colores_detectados: Lista de colores en español (ej: ["celeste", "blanco"])
        patron: Descripción del patrón detectado (opcional)

    Returns:
        Lista de dicts con país, equipo, coincidencia de colores, etc.
    """
    resultados = []
    colores_lower = [c.lower().strip() for c in colores_detectados]

    for pais, info in PAISES_FUTBOL.items():
        colores_pais = [c.lower() for c in info["colores"]]

        # Calcular coincidencia de colores
        coincidencias = sum(1 for c in colores_lower if c in colores_pais)
        total_colores = max(len(colores_pais), len(colores_lower))

        if coincidencias == 0:
            continue

        score_colores = coincidencias / total_colores

        # Bonus por patrón
        score_patron = 0.0
        patron_lower = patron.lower()
        if patron_lower:
            patron_info = info["patron_tipico"].lower()
            palabras_patron = patron_lower.split()
            coincidencias_patron = sum(1 for p in palabras_patron if p in patron_info)
            score_patron = coincidencias_patron / max(len(palabras_patron), 1) * 0.3

        score_total = score_colores + score_patron

        resultados.append({
            "pais": info["nombre_completo"],
            "seleccion": info["seleccion"],
            "colores": info["colores"],
            "colores_hex": info["colores_hex"],
            "patron_tipico": info["patron_tipico"],
            "elementos": info["elementos"],
            "equipos_famosos": info["equipos_famosos"],
            "descripcion": info["descripcion"],
            "score_coincidencia": round(score_total, 3),
            "coincidencia_colores": f"{coincidencias}/{len(colores_pais)}",
        })

    # Ordenar por score descendente
    resultados.sort(key=lambda x: x["score_coincidencia"], reverse=True)
    return resultados


def generar_contexto_pais(pais: str) -> str:
    """
    Genera contexto adicional para el prompt basado en el país identificado.

    Args:
        pais: Nombre del país (ej: "argentina")

    Returns:
        String con contexto para el prompt
    """
    info = PAISES_FUTBOL.get(pais.lower())
    if not info:
        return f"País no encontrado en la base de datos. Colores detectados en la imagen."

    return f"""País detectado: {info['nombre_completo']} ({info['seleccion']})
Colores típicos: {', '.join(info['colores'])}
Patrón característico: {info['patron_tipico']}
Elementos distintivos: {', '.join(info['elementos'])}
Equipos asociados: {', '.join(info['equipos_famosos'][:5])}
Descripción de referencia: {info['descripcion']}"""


def construir_prompt_identificacion(
    colores: list[str] = None,
    patron: str = "",
    estructura: str = "",
    contexto_extra: str = "",
) -> str:
    """
    Construye el prompt completo de identificación con el contexto detectado.

    Args:
        colores: Lista de colores detectados por el sistema visual
        patron: Patrón/diseño detectado
        estructura: Estructura detectada (cuello, mangas, etc.)
        contexto_extra: Contexto adicional del usuario

    Returns:
        Prompt formateado listo para enviar al LLM
    """
    colores_str = ", ".join(colores) if colores else "no detectados"
    patron_str = patron if patron else "no detectado"
    estructura_str = estructura if estructura else "no detectada"
    contexto_adicional = contexto_extra if contexto_extra else "Sin contexto adicional."

    return IDENTIFICATION_PROMPT.format(
        contexto_adicional=contexto_adicional,
        colores_detectados=colores_str,
        patron_detectados=patron_str,
        estructura_detectada=estructura_str,
    )


# =============================================================================
# PROMPT PARA BÚSQUEDA SIMILAR POR PAÍS
# =============================================================================

SEARCH_SIMILAR_PROMPT = """Eres un motor de búsqueda visual de camisetas deportivas.

El usuario subió una imagen de camiseta. Tu tarea es:
1. Identificar el país y equipo que representa
2. Buscar en la base de datos camisetas del MISMO país/equipo
3. Filtrar por colores y patrón similares
4. Devolver los resultados más relevantes

Criterios de matching (en orden de prioridad):
1. **País/Equipo**: Debe coincidir el país o equipo
2. **Colores principales**: Deben ser los mismos o muy similares
3. **Patron/diseño**: Rayas, franjas, degradados deben coincidir
4. **Elementos distintivos**: Escudo, marca, dorsales

NO devuelvas camisetas de países diferentes aunque tengan colores similares.
Si la imagen es de Argentina, SOLO devuelve camisetas argentinas.

Formato de respuesta:
- Lista ordenada por relevancia
- Cada resultado con: nombre, país, equipo, colores, score de similitud
- Explicación breve de por qué coincide"""


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "IDENTIFICATION_SYSTEM_PROMPT",
    "IDENTIFICATION_PROMPT",
    "SEARCH_SIMILAR_PROMPT",
    "PAISES_FUTBOL",
    "COLOR_A_PAISES",
    "identificar_pais_equipo",
    "generar_contexto_pais",
    "construir_prompt_identificacion",
]
