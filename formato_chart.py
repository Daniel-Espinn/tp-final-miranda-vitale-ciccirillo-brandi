"""
Formato de texto de los charts: charts/<archivo de audio>.txt

    # cancion: believer.wav
    # beats: 0.512 0.981 1.450 1.919 2.388 2.857
    0.512 1
    0.512 2
    0.981 0
    1.450 2 0.750
    2.388 4

Las dos primeras líneas son encabezados. Después va una nota por línea:

    tiempo(segundos)  carril  [duración(segundos)]

La duración es opcional (solo para notas sostenidas). Las líneas vacías se
ignoran, y cualquier otra línea que empiece con # es un comentario.

Para leer un chart desde el juego:

    from formato_chart import leer_chart
    chart = leer_chart("charts/believer.wav.txt")
    chart["cancion"]   # "believer.wav"
    chart["beats"]     # [0.512, 0.981, ...]
    chart["notas"]     # [(0.512, 1, 0.0), (0.512, 2, 0.0), (1.45, 2, 0.75), ...]
"""

import dataclasses

# Qué dificultad de autochart se guarda en el archivo (resultado.notas[DIFICULTAD])
DIFICULTAD = "experto"

# Nombres que se prueban para leer cada campo de una nota de autochart.
# Si tu clase Nota usa otros nombres, agregalos acá.
_CAMPOS_TIEMPO = ("tiempo", "t", "time", "inicio", "start", "segundo", "segundos")
_CAMPOS_CARRIL = ("trastes", "traste", "carril", "lane", "fret", "frets", "columna", "col", "boton")
_CAMPOS_DURACION = ("duracion", "duration", "sustain", "largo", "dur", "longitud")


class ErrorChart(ValueError):
    """Error de formato en un chart; `linea` es el número de línea (desde 1)."""

    def __init__(self, linea, mensaje):
        super().__init__(mensaje)
        self.linea = linea


# ---------------------------------------------------------------------------
# resultado de autochart -> texto
# ---------------------------------------------------------------------------
def _campo(nota, candidatos):
    for nombre in candidatos:
        if isinstance(nota, dict):
            if nombre in nota:
                return nota[nombre]
        elif hasattr(nota, nombre):
            return getattr(nota, nombre)
    return None


def _campos(nota):
    """Lista los campos de una nota (solo para armar mensajes de error)."""
    if isinstance(nota, dict):
        return list(nota.keys())
    if dataclasses.is_dataclass(nota) and not isinstance(nota, type):
        return [f.name for f in dataclasses.fields(nota)]
    if hasattr(nota, "_fields"):
        return list(nota._fields)
    if hasattr(nota, "__dict__"):
        return list(vars(nota).keys())
    return []


def _a_carriles(valor):
    """
    Un traste suelto o una colección de trastes (un acorde) -> lista de enteros.
    Una colección vacía se toma como nota al aire (carril 0).
    """
    try:
        carriles = sorted({int(c) for c in valor})
    except TypeError:
        carriles = [int(valor)]
    return carriles or [0]


def _leer_nota(nota):
    """Devuelve (tiempo, lista_de_carriles, duracion) de una nota de autochart."""
    posicional = isinstance(nota, (tuple, list)) and not hasattr(nota, "_fields")
    if posicional and len(nota) >= 2:
        tiempo, carril = nota[0], nota[1]
        duracion = nota[2] if len(nota) > 2 else 0
    else:
        tiempo = _campo(nota, _CAMPOS_TIEMPO)
        carril = _campo(nota, _CAMPOS_CARRIL)
        duracion = _campo(nota, _CAMPOS_DURACION)

    if tiempo is None or carril is None:
        raise ValueError(
            f"No reconozco los campos de la nota ({type(nota).__name__}): {_campos(nota)}. "
            "Ajustá _CAMPOS_TIEMPO / _CAMPOS_CARRIL / _CAMPOS_DURACION en formato_chart.py."
        )
    return float(tiempo), _a_carriles(carril), float(duracion or 0.0)


def resultado_a_texto(resultado, nombre_cancion):
    """Convierte el resultado de autochart.generar al texto del chart."""
    beats = [float(b) for b in resultado.beats]

    try:
        notas = resultado.notas[DIFICULTAD]
    except (KeyError, TypeError):
        disponibles = list(resultado.notas.keys()) if hasattr(resultado.notas, "keys") else "?"
        raise ValueError(
            f"autochart no devolvió la dificultad «{DIFICULTAD}» (hay: {disponibles})."
        )

    lineas = [
        f"# cancion: {nombre_cancion}",
        "# beats: " + " ".join(f"{b:.3f}" for b in beats),
    ]
    for nota in notas:
        tiempo, carriles, duracion = _leer_nota(nota)
        for carril in carriles:  # un acorde son varias líneas con el mismo tiempo
            linea = f"{tiempo:.3f} {carril}"
            if duracion > 0:
                linea += f" {duracion:.3f}"
            lineas.append(linea)
    return "\n".join(lineas) + "\n"


# ---------------------------------------------------------------------------
# texto -> datos (para el juego y para validar lo que se edita)
# ---------------------------------------------------------------------------
def parsear_chart(texto):
    """
    Lee el texto de un chart. Devuelve {"cancion", "beats", "notas"}.
    Lanza ErrorChart (con el número de línea) si el formato no es válido.
    """
    cancion = None
    beats = None
    notas = []

    for n, crudo in enumerate(texto.split("\n"), start=1):
        linea = crudo.strip()
        if not linea:
            continue

        if linea.startswith("#"):
            clave, separador, valor = linea[1:].partition(":")
            clave = clave.strip().lower()
            if separador and clave == "cancion":
                cancion = valor.strip()
            elif separador and clave == "beats":
                try:
                    beats = [float(x) for x in valor.split()]
                except ValueError:
                    raise ErrorChart(n, "Los beats tienen que ser números separados por espacios.")
            continue  # cualquier otro comentario se ignora

        partes = linea.split()
        if len(partes) not in (2, 3):
            raise ErrorChart(n, "Cada nota es: tiempo carril [duración].")
        try:
            tiempo = float(partes[0])
            carril = int(partes[1])
            duracion = float(partes[2]) if len(partes) == 3 else 0.0
        except ValueError:
            raise ErrorChart(
                n, "Formato inválido: tiempo (decimal), carril (entero) y duración opcional (decimal)."
            )
        if tiempo < 0 or duracion < 0:
            raise ErrorChart(n, "El tiempo y la duración no pueden ser negativos.")
        notas.append((tiempo, carril, duracion))

    if cancion is None:
        raise ErrorChart(1, "Falta la línea «# cancion: nombre.wav».")
    if beats is None:
        raise ErrorChart(1, "Falta la línea «# beats: ...».")
    return {"cancion": cancion, "beats": beats, "notas": notas}


def leer_chart(ruta):
    """Lee un archivo de chart del disco (ver parsear_chart)."""
    with open(ruta, "r", encoding="utf-8") as f:
        return parsear_chart(f.read())


def validar_texto(texto):
    """Para el editor: None si el texto está bien, o (numero_de_linea, mensaje)."""
    try:
        parsear_chart(texto)
    except ErrorChart as e:
        return e.linea, str(e)
    return None