import os
import shutil
import threading
import traceback

import pygame

from editor_texto import EditorTexto
from formato_chart import resultado_a_texto, validar_texto

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
CARPETA_CANCIONES = "canciones"
CARPETA_CHARTS = "charts"
ARCHIVO_LISTA = os.path.join(CARPETA_CHARTS, "canciones.txt")
EXTENSIONES = {".wav", ".mp3", ".ogg", ".flac"}

ANCHO, ALTO = 800, 600
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


# ---------------------------------------------------------------------------
# Lógica de canciones (sin pygame, se puede reutilizar desde otras pantallas)
# ---------------------------------------------------------------------------
def escanear_canciones():
    """Devuelve las rutas (relativas a canciones/) de todos los audios, ordenadas."""
    encontradas = []
    for carpeta, _, archivos in os.walk(CARPETA_CANCIONES):
        for archivo in archivos:
            if os.path.splitext(archivo)[1].lower() in EXTENSIONES:
                ruta = os.path.join(carpeta, archivo)
                encontradas.append(os.path.relpath(ruta, CARPETA_CANCIONES))
    return sorted(encontradas, key=str.lower)


def guardar_lista(canciones):
    """Guarda la lista en charts/canciones.txt, una ruta por línea."""
    os.makedirs(CARPETA_CHARTS, exist_ok=True)
    with open(ARCHIVO_LISTA, "w", encoding="utf-8") as f:
        for ruta in canciones:
            f.write(ruta.replace(os.sep, "/") + "\n")


def ruta_chart(nombre):
    """Dónde se guarda el chart de una canción: charts/<archivo>.txt"""
    return os.path.join(CARPETA_CHARTS, os.path.basename(nombre) + ".txt")


def guardar_chart(resultado, nombre):
    """Convierte el resultado de autochart a texto y lo guarda en charts/."""
    texto = resultado_a_texto(resultado, os.path.basename(nombre))
    error = validar_texto(texto)
    if error:  # no debería pasar: el chart tiene que poder abrirse en el editor
        raise ValueError(f"El chart generado no es válido (línea {error[0]}): {error[1]}")
    os.makedirs(CARPETA_CHARTS, exist_ok=True)
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
    if os.path.splitext(nombre)[1].lower() not in EXTENSIONES:
        return False, f"Formato no soportado: {nombre}"

    nombres_existentes = {os.path.basename(r).lower() for r in escanear_canciones()}
    if nombre.lower() in nombres_existentes:
        return False, f"Ya existe una canción con el nombre «{nombre}»."

    os.makedirs(CARPETA_CANCIONES, exist_ok=True)
    shutil.copy2(ruta_origen, os.path.join(CARPETA_CANCIONES, nombre))
    guardar_lista(escanear_canciones())
    return True, f"Añadida: {nombre}"


def quitar_cancion(nombre):
    """Deshace agregar_cancion (se usa si falla la generación del chart)."""
    try:
        os.remove(os.path.join(CARPETA_CANCIONES, nombre))
    except OSError:
        pass
    try:
        if os.path.exists(ruta_chart(nombre)):
            os.remove(ruta_chart(nombre))
    except OSError:
        pass
    guardar_lista(escanear_canciones())


# ---------------------------------------------------------------------------
# Generación de charts en un hilo aparte (para no congelar la ventana)
# ---------------------------------------------------------------------------
estado = {
    "fraccion": 0.0,
    "texto": "",
    "nombre": "",
    "indice": 0,
    "total": 0,
    "ok": [],
    "errores": [],
    "terminado": False,
}
lock = threading.Lock()


def reportar(fraccion, texto):
    """Callback que autochart llama a medida que avanza."""
    with lock:
        estado["fraccion"] = fraccion
        estado["texto"] = texto
    print(f"{fraccion*100:.0f}% - {texto}")


def trabajo(nombres):
    """Pasa cada canción por autochart y guarda el resultado en charts/."""
    with lock:
        estado["texto"] = "Cargando autochart..."

    try:
        import autochart  # se importa acá para que la ventana abra rápido
    except Exception as e:
        for nombre in nombres:
            quitar_cancion(nombre)
        with lock:
            estado["errores"].append(f"No se pudo importar autochart: {e}")
            estado["terminado"] = True
        return

    for i, nombre in enumerate(nombres):
        with lock:
            estado["indice"] = i
            estado["nombre"] = nombre
            estado["fraccion"] = 0.0
            estado["texto"] = "Empezando..."
        try:
            resultado = autochart.generar(
                os.path.join(CARPETA_CANCIONES, nombre), progreso=reportar
            )
            guardar_chart(resultado, nombre)
            with lock:
                estado["ok"].append(nombre)
        except Exception as e:
            traceback.print_exc()  # el detalle completo queda en la consola
            quitar_cancion(nombre)  # así se puede volver a intentar
            with lock:
                estado["errores"].append(f"{nombre}: {e}")

    with lock:
        estado["fraccion"] = 1.0
        estado["terminado"] = True


# ---------------------------------------------------------------------------
# Selector de archivos
# ---------------------------------------------------------------------------
def elegir_archivos():
    """
    Abre el selector de archivos del sistema (tkinter).
    Devuelve (lista_de_rutas, mensaje_de_error_o_None).
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return [], "tkinter no está instalado: arrastrá el archivo a la ventana."

    try:
        raiz = tk.Tk()
        raiz.withdraw()
        raiz.attributes("-topmost", True)
        rutas = filedialog.askopenfilenames(
            title="Elegí una o más canciones",
            filetypes=[("Audio", "*.wav *.mp3 *.ogg *.flac"), ("Todos", "*.*")],
        )
        raiz.destroy()
        return list(rutas), None
    except Exception:
        return [], "No se pudo abrir el selector: arrastrá el archivo a la ventana."


# ---------------------------------------------------------------------------
# Interfaz
# ---------------------------------------------------------------------------
def recortar(texto, fuente, ancho_max):
    """Corta el texto con '...' para que entre en ancho_max píxeles."""
    if fuente.size(texto)[0] <= ancho_max:
        return texto
    while texto and fuente.size(texto + "...")[0] > ancho_max:
        texto = texto[:-1]
    return texto + "..."


def main():
    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Añadir canciones")
    fuente_titulo = pygame.font.Font(None, 64)
    fuente = pygame.font.Font(None, 32)
    fuente_chica = pygame.font.Font(None, 26)
    reloj = pygame.time.Clock()

    boton = pygame.Rect(0, 0, 300, 60)
    boton.center = (ANCHO // 2, 130)

    panel = pygame.Rect(60, 270, ANCHO - 120, 290)
    alto_fila = 30
    filas_visibles = (panel.height - 20) // alto_fila

    # Al entrar, lee las canciones y deja el archivo de texto actualizado
    canciones = escanear_canciones()
    guardar_lista(canciones)

    modo = "menu"  # "menu", "procesando" o "editor"
    editor = None
    mensaje, color_mensaje = "", COLOR_TEXTO
    errores_copia = []
    scroll = 0
    fraccion_visible = 0.0
    corriendo = True

    def procesar(rutas):
        """Copia las canciones a canciones/ y arranca la generación de charts."""
        nonlocal canciones, mensaje, color_mensaje, scroll, modo
        nonlocal errores_copia, fraccion_visible
        if not rutas:
            return

        nuevas, errores_copia = [], []
        for ruta in rutas:
            ok, texto = agregar_cancion(ruta)
            if ok:
                nuevas.append(os.path.basename(ruta))
            else:
                errores_copia.append(texto)

        canciones = escanear_canciones()
        scroll = max(0, len(canciones) - filas_visibles)

        if not nuevas:
            mensaje = errores_copia[0]
            if len(errores_copia) > 1:
                mensaje += f"  (+{len(errores_copia) - 1} errores)"
            color_mensaje = COLOR_ERROR
            return

        with lock:
            estado.update(
                fraccion=0.0, texto="Iniciando...", nombre=nuevas[0],
                indice=0, total=len(nuevas), ok=[], errores=[], terminado=False,
            )
        fraccion_visible = 0.0
        modo = "procesando"
        threading.Thread(target=trabajo, args=(nuevas,), daemon=True).start()

    def abrir_editor(ruta):
        """Abre el chart de una canción en el editor de texto."""
        nonlocal editor, modo, mensaje, color_mensaje
        archivo = ruta_chart(ruta)
        if not os.path.exists(archivo):
            mensaje, color_mensaje = "Esa canción todavía no tiene chart.", COLOR_ERROR
            return
        try:
            editor = EditorTexto(
                archivo, f"Editando: {os.path.basename(archivo)}", ANCHO, ALTO,
                validador=validar_texto,
            )
        except (OSError, UnicodeDecodeError) as e:
            mensaje, color_mensaje = f"No se pudo abrir el chart: {e}", COLOR_ERROR
            return
        pygame.key.set_repeat(400, 35)  # repetir teclas al mantenerlas apretadas
        pygame.key.start_text_input()
        mensaje = ""
        modo = "editor"

    while corriendo:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                corriendo = False
            elif modo == "editor":
                if editor.evento(evento):  # True = volver al menú
                    pygame.key.set_repeat()
                    editor = None
                    modo = "menu"
            elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                corriendo = False
            elif modo != "menu":
                continue  # mientras se genera el chart, se ignora el resto
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if boton.collidepoint(evento.pos):
                    rutas, error = elegir_archivos()
                    if error:
                        mensaje, color_mensaje = error, COLOR_ERROR
                    else:
                        procesar(rutas)
                elif panel.collidepoint(evento.pos) and evento.pos[1] >= panel.y + 12:
                    i = (evento.pos[1] - (panel.y + 12)) // alto_fila
                    if i < filas_visibles and scroll + i < len(canciones):
                        abrir_editor(canciones[scroll + i])
            elif evento.type == pygame.DROPFILE:
                procesar([evento.file])
            elif evento.type == pygame.MOUSEWHEEL:
                scroll -= evento.y
                scroll = max(0, min(scroll, max(0, len(canciones) - filas_visibles)))

        # --- Cuando el hilo termina, volver al menú con el resultado ---
        if modo == "procesando":
            with lock:
                terminado = estado["terminado"]
                ok = list(estado["ok"])
                errores = errores_copia + list(estado["errores"])
            if terminado:
                canciones = escanear_canciones()
                scroll = max(0, len(canciones) - filas_visibles)
                if errores:
                    mensaje = errores[0]
                    if len(errores) > 1:
                        mensaje += f"  (+{len(errores) - 1} errores)"
                    if ok:
                        mensaje = f"Charts listos: {len(ok)}. " + mensaje
                    color_mensaje = COLOR_ERROR
                elif len(ok) == 1:
                    mensaje, color_mensaje = f"Chart generado: {ok[0]}", COLOR_OK
                else:
                    mensaje, color_mensaje = f"Charts generados: {len(ok)}", COLOR_OK
                modo = "menu"

        pantalla.fill(COLOR_FONDO)

        if modo == "editor":
            editor.dibujar(pantalla)

        elif modo == "procesando":
            # --- Pantalla de progreso ---
            with lock:
                fraccion = estado["fraccion"]
                texto = estado["texto"]
                nombre = estado["nombre"]
                indice = estado["indice"]
                total = estado["total"]

            if fraccion < fraccion_visible:
                fraccion_visible = fraccion  # empezó otra canción
            fraccion_visible += (fraccion - fraccion_visible) * 0.15

            titulo = fuente_titulo.render("Generando chart", True, COLOR_TEXTO)
            pantalla.blit(titulo, titulo.get_rect(center=(ANCHO // 2, 150)))

            txt_nombre = fuente.render(recortar(nombre, fuente, ANCHO - 100), True, COLOR_TEXTO_SUAVE)
            pantalla.blit(txt_nombre, txt_nombre.get_rect(center=(ANCHO // 2, 210)))

            if total > 1:
                txt_cuenta = fuente_chica.render(f"Canción {indice + 1} de {total}", True, COLOR_TEXTO_SUAVE)
                pantalla.blit(txt_cuenta, txt_cuenta.get_rect(center=(ANCHO // 2, 245)))

            bx, by, bw, bh = 100, 290, ANCHO - 200, 40
            pygame.draw.rect(pantalla, COLOR_BARRA_FONDO, (bx, by, bw, bh), border_radius=12)
            relleno = int(bw * max(0.0, min(1.0, fraccion_visible)))
            if relleno > 0:
                pygame.draw.rect(pantalla, COLOR_OK, (bx, by, relleno, bh), border_radius=12)
            pct = fuente_chica.render(f"{fraccion_visible*100:.0f}%", True, COLOR_TEXTO)
            pantalla.blit(pct, pct.get_rect(center=(ANCHO // 2, by + bh // 2)))

            detalle = fuente_chica.render(recortar(texto, fuente_chica, ANCHO - 100), True, COLOR_TEXTO)
            pantalla.blit(detalle, detalle.get_rect(center=(ANCHO // 2, 370)))

        else:
            # --- Pantalla de añadir canciones ---
            titulo = fuente_titulo.render("Añadir canciones", True, COLOR_TEXTO)
            pantalla.blit(titulo, titulo.get_rect(center=(ANCHO // 2, 50)))

            pos_mouse = pygame.mouse.get_pos()
            hover = boton.collidepoint(pos_mouse)
            pygame.draw.rect(pantalla, COLOR_BOTON_HOVER if hover else COLOR_BOTON, boton, border_radius=12)
            txt_boton = fuente.render("Añadir canción", True, COLOR_TEXTO)
            pantalla.blit(txt_boton, txt_boton.get_rect(center=boton.center))

            ayuda = fuente_chica.render("o arrastrá un archivo de audio a la ventana", True, COLOR_TEXTO_SUAVE)
            pantalla.blit(ayuda, ayuda.get_rect(center=(ANCHO // 2, 195)))

            if mensaje:
                txt_msg = fuente_chica.render(recortar(mensaje, fuente_chica, ANCHO - 80), True, color_mensaje)
                pantalla.blit(txt_msg, txt_msg.get_rect(center=(ANCHO // 2, 230)))

            cabecera = fuente_chica.render(
                recortar(f"Canciones: {len(canciones)} — clic en una para ver o editar su chart",
                         fuente_chica, panel.width),
                True, COLOR_TEXTO_SUAVE,
            )
            pantalla.blit(cabecera, (panel.x, panel.y - 24))

            pygame.draw.rect(pantalla, COLOR_PANEL, panel, border_radius=10)
            if not canciones:
                vacio = fuente_chica.render("Todavía no hay canciones.", True, COLOR_TEXTO_SUAVE)
                pantalla.blit(vacio, vacio.get_rect(center=panel.center))
            else:
                for i, ruta in enumerate(canciones[scroll:scroll + filas_visibles]):
                    y = panel.y + 12 + i * alto_fila
                    fila = pygame.Rect(panel.x + 6, y - 3, panel.width - 12, alto_fila - 2)
                    if fila.collidepoint(pos_mouse):
                        pygame.draw.rect(pantalla, COLOR_FILA_HOVER, fila, border_radius=6)

                    listo = os.path.exists(ruta_chart(ruta))
                    etiqueta = fuente_chica.render(
                        "chart listo" if listo else "sin chart",
                        True, COLOR_OK if listo else COLOR_TEXTO_SUAVE,
                    )
                    pantalla.blit(etiqueta, (panel.right - 15 - etiqueta.get_width(), y))
                    ancho_nombre = panel.width - 30 - etiqueta.get_width() - 15
                    txt = fuente_chica.render(
                        recortar(ruta.replace(os.sep, "/"), fuente_chica, ancho_nombre),
                        True, COLOR_TEXTO,
                    )
                    pantalla.blit(txt, (panel.x + 15, y))

        pygame.display.flip()
        reloj.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()