"""Pantallas de la aplicación: menú (añadir canciones), progreso y editor de charts."""

import os

import pygame
from juego import jugar
import canciones
import config as cfg
from editor_texto import EditorTexto
from formato_chart import validar_texto
from generador import Generador
from explorador import Explorador, recortar


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def recortar(texto, fuente, ancho_max):
    """Corta el texto con '...' para que entre en ancho_max píxeles."""
    if fuente.size(texto)[0] <= ancho_max:
        return texto
    while texto and fuente.size(texto + "...")[0] > ancho_max:
        texto = texto[:-1]
    return texto + "..."


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
class Pantalla:
    """Interfaz común: main.py llama a estos métodos en cada fotograma."""

    def __init__(self, app):
        self.app = app

    def al_entrar(self):
        pass

    def al_salir(self):
        pass

    def evento(self, evento):
        pass

    def actualizar(self):
        pass

    def dibujar(self, superficie):
        pass


# ---------------------------------------------------------------------------
# Menú: añadir canciones y lista de la biblioteca
# ---------------------------------------------------------------------------

class PantallaMenu(Pantalla):
    def __init__ (self, app):
        super().__init__(app)
        self.botones= []
        texto_botones=["Jugar", "Cargar canciones", "Settings"]
        for i in range(len(texto_botones)):
            rect = pygame.Rect(0, 0, 300, 60)
            rect.center = (cfg.ANCHO // 2, 220 + i * 90)
            self.botones.append((texto_botones[i], rect))
        self.mensaje = ""

    def _clic(self, texto):
        if texto == "Cargar canciones":
            self.app.cambiar(self.app.cargar)
        elif texto == "Jugar":
            self.app.cambiar(self.app.elegir)
        else:
            self.mensaje = f"{texto}: todavía no está hecho"
 

    def evento(self, evento):
        if (evento.type == pygame.KEYDOWN) and (evento.key == pygame.K_ESCAPE):
            self.app.salir()
        elif (evento.type == pygame.MOUSEBUTTONDOWN) and (evento.button == 1):
            for texto, rect in self.botones:
                if rect.collidepoint(evento.pos):
                    self._clic(texto)

    def dibujar(self, s):
            app = self.app
            s.fill(cfg.COLOR_FONDO)

            pos_mouse = pygame.mouse.get_pos()
            for texto, rect in self.botones:
                color = cfg.COLOR_BOTON_HOVER if rect.collidepoint(pos_mouse) else cfg.COLOR_BOTON
                pygame.draw.rect(s, color, rect, border_radius=12)
                txt = self.app.fuente.render(texto, True, cfg.COLOR_TEXTO)
                s.blit(txt, txt.get_rect(center=rect.center))

            if self.mensaje:
                txt = self.app.fuente_chica.render(self.mensaje, True, cfg.COLOR_TEXTO_SUAVE)
                s.blit(txt, txt.get_rect(center=(cfg.ANCHO // 2, 520)))


class PantallaCargarCanciones(Pantalla):
    ALTO_FILA = 30

    def __init__(self, app):
        super().__init__(app)
        self.boton = pygame.Rect(0, 0, 300, 60)
        self.boton.center = (cfg.ANCHO // 2, 130)
        self.panel = pygame.Rect(60, 270, cfg.ANCHO - 120, 290)
        self.filas_visibles = (self.panel.height - 20) // self.ALTO_FILA

        self.lista = []
        self.scroll = 0
        self.mensaje = ""
        self.color_mensaje = cfg.COLOR_TEXTO
        self.ultima_carpeta = None
        self.recargar()
        

    # --- Estado ---
    def recargar(self, al_final=False):
        self.lista = canciones.escanear_canciones()
        canciones.guardar_lista(self.lista)
        maximo = max(0, len(self.lista) - self.filas_visibles)
        self.scroll = maximo if al_final else min(self.scroll, maximo)

    def mostrar_mensaje(self, texto, color):
        self.mensaje = texto
        self.color_mensaje = color

    # --- Acciones ---
    def _procesar(self, rutas):
        """Copia las canciones a canciones/ y pasa a la pantalla de progreso."""
        if not rutas:
            return

        nuevas, errores = [], []
        for ruta in rutas:
            ok, texto = canciones.agregar_cancion(ruta)
            if ok:
                nuevas.append(os.path.basename(ruta))
            else:
                errores.append(texto)
        self.recargar(al_final=True)

        if not nuevas:
            texto = errores[0]
            if len(errores) > 1:
                texto += f"  (+{len(errores) - 1} errores)"
            self.mostrar_mensaje(texto, cfg.COLOR_ERROR)
            return

        self.app.cambiar(PantallaProgreso(self.app, nuevas, errores))

    def _abrir_editor(self, ruta):
        if not canciones.tiene_chart(ruta):
            self.mostrar_mensaje("Esa canción todavía no tiene chart.", cfg.COLOR_ERROR)
            return
        try:
            pantalla = PantallaEditor(self.app, canciones.ruta_chart(ruta))
        except (OSError, UnicodeDecodeError) as e:
            self.mostrar_mensaje(f"No se pudo abrir el chart: {e}", cfg.COLOR_ERROR)
            return
        self.mensaje = ""
        self.app.cambiar(pantalla)

    # --- Pantalla ---
    def evento(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.cambiar(self.app.menu) 
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.boton.collidepoint(e.pos):
                self.abrir_explorador()
            elif self.panel.collidepoint(e.pos) and e.pos[1] >= self.panel.y + 12:
                i = (e.pos[1] - (self.panel.y + 12)) // self.ALTO_FILA
                if i < self.filas_visibles and self.scroll + i < len(self.lista):
                    self._abrir_editor(self.lista[self.scroll + i])
        elif e.type == pygame.DROPFILE:
            self._procesar([e.file])
        elif e.type == pygame.MOUSEWHEEL:
            maximo = max(0, len(self.lista) - self.filas_visibles)
            self.scroll = max(0, min(self.scroll - e.y, maximo))

    def dibujar(self, s):
        app = self.app
        s.fill(cfg.COLOR_FONDO)

        titulo = app.fuente_titulo.render("Añadir canciones", True, cfg.COLOR_TEXTO)
        s.blit(titulo, titulo.get_rect(center=(cfg.ANCHO // 2, 50)))

        pos_mouse = pygame.mouse.get_pos()
        color_boton = cfg.COLOR_BOTON_HOVER if self.boton.collidepoint(pos_mouse) else cfg.COLOR_BOTON
        pygame.draw.rect(s, color_boton, self.boton, border_radius=12)
        txt_boton = app.fuente.render("Añadir canción", True, cfg.COLOR_TEXTO)
        s.blit(txt_boton, txt_boton.get_rect(center=self.boton.center))

        ayuda = app.fuente_chica.render(
            "o arrastrá un archivo de audio a la ventana", True, cfg.COLOR_TEXTO_SUAVE
        )
        s.blit(ayuda, ayuda.get_rect(center=(cfg.ANCHO // 2, 195)))

        if self.mensaje:
            texto = recortar(self.mensaje, app.fuente_chica, cfg.ANCHO - 80)
            txt = app.fuente_chica.render(texto, True, self.color_mensaje)
            s.blit(txt, txt.get_rect(center=(cfg.ANCHO // 2, 230)))

        cabecera = recortar(
            f"Canciones: {len(self.lista)} — clic en una para ver o editar su chart",
            app.fuente_chica, self.panel.width,
        )
        s.blit(app.fuente_chica.render(cabecera, True, cfg.COLOR_TEXTO_SUAVE),
               (self.panel.x, self.panel.y - 24))

        pygame.draw.rect(s, cfg.COLOR_PANEL, self.panel, border_radius=10)
        if not self.lista:
            vacio = app.fuente_chica.render("Todavía no hay canciones.", True, cfg.COLOR_TEXTO_SUAVE)
            s.blit(vacio, vacio.get_rect(center=self.panel.center))
            return

        visibles = self.lista[self.scroll:self.scroll + self.filas_visibles]
        for i, ruta in enumerate(visibles):
            y = self.panel.y + 12 + i * self.ALTO_FILA
            fila = pygame.Rect(self.panel.x + 6, y - 3, self.panel.width - 12, self.ALTO_FILA - 2)
            if fila.collidepoint(pos_mouse):
                pygame.draw.rect(s, cfg.COLOR_FILA_HOVER, fila, border_radius=6)

            listo = canciones.tiene_chart(ruta)
            etiqueta = app.fuente_chica.render(
                "chart listo" if listo else "sin chart",
                True, cfg.COLOR_OK if listo else cfg.COLOR_TEXTO_SUAVE,
            )
            s.blit(etiqueta, (self.panel.right - 15 - etiqueta.get_width(), y))

            ancho_nombre = self.panel.width - 30 - etiqueta.get_width() - 15
            nombre = recortar(ruta.replace(os.sep, "/"), app.fuente_chica, ancho_nombre)
            s.blit(app.fuente_chica.render(nombre, True, cfg.COLOR_TEXTO), (self.panel.x + 15, y))

    def abrir_explorador(self):
        carpeta = self.ultima_carpeta or os.path.expanduser("~")
        self.app.cambiar(PantallaExplorador(self.app, carpeta))


class PantallaExplorador(Pantalla):
    """
    Muestra carpetas y audios. Clic en una carpeta la abre, clic en una canción
    la marca o desmarca (se conservan las marcas al cambiar de carpeta).
    """
    def __init__(self, app, carpeta_inicial):
        super().__init__(app)
        self.explorador = Explorador(carpeta_inicial, app.fuente, app.fuente_chica)

    def evento(self, e):
        rutas = self.explorador.evento(e)
        if rutas is not None:
            self._terminar(rutas)

    def _terminar(self, rutas):
        """Vuelve a 'Añadir canciones' y, si hay canciones elegidas, las procesa."""
        cargar = self.app.cargar
        cargar.ultima_carpeta = self.explorador.carpeta
        self.app.cambiar(cargar)
        cargar._procesar(rutas)  # con una lista vacía no hace nada

    def dibujar(self, s):
        self.explorador.dibujar(s)

# ---------------------------------------------------------------------------
# Progreso: genera el chart con autochart mientras muestra la barra
# ---------------------------------------------------------------------------
class PantallaProgreso(Pantalla):
    def __init__(self, app, nombres, errores_previos=None):
        super().__init__(app)
        self.generador = Generador(nombres)
        self.errores_previos = list(errores_previos or [])
        self.est = self.generador.estado()
        self.fraccion_visible = 0.0  # para que la barra se anime suave

    def al_entrar(self):
        self.generador.iniciar()

    def evento(self, e):
        # Mientras se genera el chart se ignora todo salvo salir
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.salir()

    def actualizar(self):
        self.est = self.generador.estado()
        if self.est["fraccion"] < self.fraccion_visible:
            self.fraccion_visible = self.est["fraccion"]  # empezó otra canción
        self.fraccion_visible += (self.est["fraccion"] - self.fraccion_visible) * 0.15

        if self.est["terminado"]:
            self._terminar()

    def _terminar(self):
        """Vuelve al menú con un mensaje con el resultado."""
        ok = self.est["ok"]
        errores = self.errores_previos + self.est["errores"]
        menu = self.app.cargar
        menu.recargar(al_final=True)

        if errores:
            texto = errores[0]
            if len(errores) > 1:
                texto += f"  (+{len(errores) - 1} errores)"
            if ok:
                texto = f"Charts listos: {len(ok)}. " + texto
            menu.mostrar_mensaje(texto, cfg.COLOR_ERROR)
        elif len(ok) == 1:
            menu.mostrar_mensaje(f"Chart generado: {ok[0]}", cfg.COLOR_OK)
        else:
            menu.mostrar_mensaje(f"Charts generados: {len(ok)}", cfg.COLOR_OK)
        self.app.cambiar(menu)

    def dibujar(self, s):
        app, est = self.app, self.est
        s.fill(cfg.COLOR_FONDO)

        titulo = app.fuente_titulo.render("Generando chart", True, cfg.COLOR_TEXTO)
        s.blit(titulo, titulo.get_rect(center=(cfg.ANCHO // 2, 150)))

        nombre = recortar(est["nombre"], app.fuente, cfg.ANCHO - 100)
        txt_nombre = app.fuente.render(nombre, True, cfg.COLOR_TEXTO_SUAVE)
        s.blit(txt_nombre, txt_nombre.get_rect(center=(cfg.ANCHO // 2, 210)))

        if est["total"] > 1:
            cuenta = app.fuente_chica.render(
                f"Canción {est['indice'] + 1} de {est['total']}", True, cfg.COLOR_TEXTO_SUAVE
            )
            s.blit(cuenta, cuenta.get_rect(center=(cfg.ANCHO // 2, 245)))

        bx, by, bw, bh = 100, 290, cfg.ANCHO - 200, 40
        pygame.draw.rect(s, cfg.COLOR_BARRA_FONDO, (bx, by, bw, bh), border_radius=12)
        relleno = int(bw * max(0.0, min(1.0, self.fraccion_visible)))
        if relleno > 0:
            pygame.draw.rect(s, cfg.COLOR_OK, (bx, by, relleno, bh), border_radius=12)
        pct = app.fuente_chica.render(f"{self.fraccion_visible*100:.0f}%", True, cfg.COLOR_TEXTO)
        s.blit(pct, pct.get_rect(center=(cfg.ANCHO // 2, by + bh // 2)))

        detalle = recortar(est["texto"], app.fuente_chica, cfg.ANCHO - 100)
        txt = app.fuente_chica.render(detalle, True, cfg.COLOR_TEXTO)
        s.blit(txt, txt.get_rect(center=(cfg.ANCHO // 2, 370)))


# ---------------------------------------------------------------------------
# Editor: ver y editar el chart de una canción
# ---------------------------------------------------------------------------
class PantallaEditor(Pantalla):
    def __init__(self, app, archivo):
        super().__init__(app)
        self.editor = EditorTexto(
            archivo, f"Editando: {os.path.basename(archivo)}", cfg.ANCHO, cfg.ALTO,
            validador=validar_texto,
        )

    def al_entrar(self):
        pygame.key.set_repeat(400, 35)  # repetir teclas al mantenerlas apretadas
        pygame.key.start_text_input()

    def al_salir(self):
        pygame.key.set_repeat()

    def evento(self, e):
        if self.editor.evento(e):  # True = el usuario quiere volver
            self.app.cambiar(self.app.cargar)

    def dibujar(self, s):
        self.editor.dibujar(s)


# ---------------------------------------------------------------------------
# Elegir canción: lista de canciones para jugar
# ---------------------------------------------------------------------------
class PantallaElegirCancion(Pantalla):
    ALTO_FILA = 30

    def __init__(self, app):
        super().__init__(app)
        self.panel = pygame.Rect(60, 120, cfg.ANCHO - 120, 420)
        self.filas_visibles = (self.panel.height - 20) // self.ALTO_FILA
        self.lista = []
        self.scroll = 0
        self.mensaje = ""
        self.color_mensaje = cfg.COLOR_TEXTO

    def al_entrar(self):
        self.lista = canciones.escanear_canciones()  # relee las canciones cada vez que entrás
        self.scroll = 0
        self.mensaje = ""

    def evento(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.cambiar(self.app.menu)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.panel.collidepoint(e.pos) and e.pos[1] >= self.panel.y + 12:
                i = (e.pos[1] - (self.panel.y + 12)) // self.ALTO_FILA
                if i < self.filas_visibles and self.scroll + i < len(self.lista):
                    ruta = self.lista[self.scroll + i]
                    if canciones.tiene_chart(ruta):
                        if not jugar(self.app.ventana, ruta):
                            self.app.salir()  
                    else:
                        self.mensaje = "Esa canción todavía no tiene chart."
                        self.color_mensaje = cfg.COLOR_ERROR
        elif e.type == pygame.MOUSEWHEEL:
            maximo = max(0, len(self.lista) - self.filas_visibles)
            self.scroll = max(0, min(self.scroll - e.y, maximo))

    def dibujar(self, s):
        app = self.app
        s.fill(cfg.COLOR_FONDO)

        titulo = app.fuente_titulo.render("Elegí una canción", True, cfg.COLOR_TEXTO)
        s.blit(titulo, titulo.get_rect(center=(cfg.ANCHO // 2, 50)))

        if self.mensaje:
            texto = recortar(self.mensaje, app.fuente_chica, cfg.ANCHO - 80)
            txt = app.fuente_chica.render(texto, True, self.color_mensaje)
            s.blit(txt, txt.get_rect(center=(cfg.ANCHO // 2, 95)))

        pygame.draw.rect(s, cfg.COLOR_PANEL, self.panel, border_radius=10)
        if not self.lista:
            vacio = app.fuente_chica.render("Todavía no hay canciones.", True, cfg.COLOR_TEXTO_SUAVE)
            s.blit(vacio, vacio.get_rect(center=self.panel.center))
            return

        pos_mouse = pygame.mouse.get_pos()
        visibles = self.lista[self.scroll:self.scroll + self.filas_visibles]
        for i, ruta in enumerate(visibles):
            y = self.panel.y + 12 + i * self.ALTO_FILA
            fila = pygame.Rect(self.panel.x + 6, y - 3, self.panel.width - 12, self.ALTO_FILA - 2)
            if fila.collidepoint(pos_mouse):
                pygame.draw.rect(s, cfg.COLOR_FILA_HOVER, fila, border_radius=6)

            listo = canciones.tiene_chart(ruta)
            etiqueta = app.fuente_chica.render(
                "chart listo" if listo else "sin chart",
                True, cfg.COLOR_OK if listo else cfg.COLOR_TEXTO_SUAVE,
            )
            s.blit(etiqueta, (self.panel.right - 15 - etiqueta.get_width(), y))

            ancho_nombre = self.panel.width - 30 - etiqueta.get_width() - 15
            nombre = recortar(ruta.replace(os.sep, "/"), app.fuente_chica, ancho_nombre)
            s.blit(app.fuente_chica.render(nombre, True, cfg.COLOR_TEXTO), (self.panel.x + 15, y))