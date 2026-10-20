"""Biblioteca de canciones: lectura de canciones/, lista en charts/ y charts en texto."""

import os
import shutil

import config as cfg
from formato_chart import resultado_a_texto, validar_texto


def escanear_canciones():
    """Devuelve las rutas (relativas a canciones/) de todos los audios, ordenadas."""
    encontradas = []
    for carpeta, _, archivos in os.walk(cfg.CARPETA_CANCIONES):
        for archivo in archivos:
            if os.path.splitext(archivo)[1].lower() in cfg.EXTENSIONES:
                ruta = os.path.join(carpeta, archivo)
                encontradas.append(os.path.relpath(ruta, cfg.CARPETA_CANCIONES))
    return sorted(encontradas, key=str.lower)


def guardar_lista(lista):
    """Guarda la lista en charts/canciones.txt, una ruta por línea."""
    os.makedirs(cfg.CARPETA_CHARTS, exist_ok=True)
    with open(cfg.ARCHIVO_LISTA, "w", encoding="utf-8") as f:
        for ruta in lista:
            f.write(ruta.replace(os.sep, "/") + "\n")


def ruta_chart(nombre):
    """Dónde se guarda el chart de una canción: charts/<archivo>.txt"""
    return os.path.join(cfg.CARPETA_CHARTS, os.path.basename(nombre) + ".txt")


def tiene_chart(nombre):
    return os.path.exists(ruta_chart(nombre))


def guardar_chart(resultado, nombre):
    """Convierte el resultado de autochart a texto y lo guarda en charts/."""
    texto = resultado_a_texto(resultado, os.path.basename(nombre))
    error = validar_texto(texto)
    if error:  # no debería pasar: el chart tiene que poder abrirse en el editor
        raise ValueError(f"El chart generado no es válido (línea {error[0]}): {error[1]}")
    os.makedirs(cfg.CARPETA_CHARTS, exist_ok=True)
    with open(ruta_chart(nombre), "w", encoding="utf-8") as f:
        f.write(texto)


def agregar_cancion(ruta_origen):
    """
    Copia una canción a canciones/ y actualiza charts/canciones.txt.
    Rechaza archivos que no sean audio o cuyo nombre ya exista en la biblioteca
    (se compara solo el nombre de archivo, sin importar la subcarpeta).
    Devuelve (ok, mensaje).
    """
    if not os.path.isfile(ruta_origen):
        return False, "El archivo no existe."

    nombre = os.path.basename(ruta_origen)
    if os.path.splitext(nombre)[1].lower() not in cfg.EXTENSIONES:
        return False, f"Formato no soportado: {nombre}"

    nombres_existentes = {os.path.basename(r).lower() for r in escanear_canciones()}
    if nombre.lower() in nombres_existentes:
        return False, f"Ya existe una canción con el nombre «{nombre}»."

    os.makedirs(cfg.CARPETA_CANCIONES, exist_ok=True)
    shutil.copy2(ruta_origen, os.path.join(cfg.CARPETA_CANCIONES, nombre))
    guardar_lista(escanear_canciones())
    return True, f"Añadida: {nombre}"


def quitar_cancion(nombre):
    """Deshace agregar_cancion (se usa si falla la generación del chart)."""
    try:
        os.remove(os.path.join(cfg.CARPETA_CANCIONES, nombre))
    except OSError:
        pass
    try:
        if tiene_chart(nombre):
            os.remove(ruta_chart(nombre))
    except OSError:
        pass
    guardar_lista(escanear_canciones())