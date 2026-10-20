"""Constantes compartidas por todo el proyecto."""

import os

# Carpetas y archivos
CARPETA_CANCIONES = "canciones"
CARPETA_CHARTS = "charts"
ARCHIVO_LISTA = os.path.join(CARPETA_CHARTS, "canciones.txt")
EXTENSIONES = {".wav", ".mp3", ".ogg", ".flac"}

# Ventana
TITULO = "Charts"
ANCHO, ALTO = 800, 600
FPS = 60

# Colores
COLOR_FONDO = (20, 20, 40)
COLOR_TEXTO = (255, 255, 255)
COLOR_TEXTO_SUAVE = (170, 170, 200)
COLOR_BOTON = (60, 60, 110)
COLOR_BOTON_HOVER = (85, 85, 150)
COLOR_OK = (80, 200, 120)
COLOR_ERROR = (255, 100, 100)
COLOR_PANEL = (30, 30, 58)
COLOR_FILA_HOVER = (45, 45, 85)
COLOR_BARRA_FONDO = (60, 60, 90)