import os

import pygame

COLOR_FONDO = (20, 20, 40)
COLOR_PANEL = (30, 30, 58)
COLOR_LINEA_ACTUAL = (40, 40, 76)
COLOR_GUTTER = (24, 24, 48)
COLOR_TEXTO = (255, 255, 255)
COLOR_TEXTO_SUAVE = (170, 170, 200)
COLOR_OK = (80, 200, 120)
COLOR_ERROR = (255, 100, 100)


class EditorTexto:
    """
    Editor de texto simple para pygame.

    `validador` (opcional) es una función validador(texto) que devuelve None si el
    texto está bien, o (numero_de_linea, mensaje) si no. Ctrl+S no guarda mientras
    el validador marque un error.

    Uso desde el loop principal:
        editor = EditorTexto(ruta, "Titulo", ANCHO, ALTO)
        ...
        if editor.evento(evento):   # True = el usuario quiere volver
            editor = None
        ...
        editor.dibujar(pantalla)

    Teclas: flechas, Inicio/Fin, Re Pág/Av Pág, Ctrl+Inicio/Fin, Enter, Tab,
    Backspace, Supr, Ctrl+S (guardar) y Esc (volver). Rueda del mouse y clic.
    """

    def __init__(self, ruta, titulo, ancho, alto, validador=None):
        self.ruta = ruta
        self.titulo = titulo
        self.validador = validador
        self.ancho = ancho
        self.alto = alto

        with open(ruta, "r", encoding="utf-8") as f:
            self.lineas = f.read().split("\n")
        if len(self.lineas) > 1 and self.lineas[-1] == "":
            self.lineas.pop()  # el salto de línea final no es una línea más

        self.cy = 0  # línea del cursor
        self.cx = 0  # columna del cursor
        self.scroll_y = 0  # en líneas
        self.scroll_x = 0  # en píxeles
        self.modificado = False
        self.descarte_pendiente = False
        self.mensaje = ""
        self.color_mensaje = COLOR_TEXTO_SUAVE

        nombre_mono = pygame.font.match_font(
            "dejavusansmono,consolas,couriernew,liberationmono,monospace"
        )
        self.fuente = (
            pygame.font.Font(nombre_mono, 18) if nombre_mono else pygame.font.Font(None, 22)
        )
        self.fuente_titulo = pygame.font.Font(None, 30)
        self.fuente_chica = pygame.font.Font(None, 24)

        self.alto_linea = self.fuente.get_linesize()
        self.ancho_char = max(1, self.fuente.size("M")[0])
        self.ancho_gutter = 64
        self.area = pygame.Rect(0, 52, ancho, alto - 52 - 34)
        self.area_texto = pygame.Rect(
            self.area.x + self.ancho_gutter,
            self.area.y,
            self.area.width - self.ancho_gutter,
            self.area.height,
        )
        self.visibles = max(1, self.area.height // self.alto_linea)

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def _msg(self, texto, color):
        self.mensaje = texto
        self.color_mensaje = color

    def _recortar(self, texto, fuente, ancho_max):
        if fuente.size(texto)[0] <= ancho_max:
            return texto
        while texto and fuente.size(texto + "...")[0] > ancho_max:
            texto = texto[:-1]
        return texto + "..."

    def _ver_cursor(self):
        """Hace scroll para que el cursor quede a la vista."""
        if self.cy < self.scroll_y:
            self.scroll_y = self.cy
        elif self.cy >= self.scroll_y + self.visibles:
            self.scroll_y = self.cy - self.visibles + 1

        x = self.fuente.size(self.lineas[self.cy][: self.cx])[0]
        margen = 40
        ancho_visible = self.area_texto.width - 16
        if x - self.scroll_x > ancho_visible - margen:
            self.scroll_x = x - ancho_visible + margen
        elif x - self.scroll_x < margen:
            self.scroll_x = max(0, x - margen)

    def _col_desde_x(self, linea, objetivo):
        """Columna más cercana a una posición en píxeles dentro de la línea."""
        if objetivo <= 0:
            return 0

        def ancho(c):
            return self.fuente.size(linea[:c])[0]

        bajo, alto = 0, len(linea)
        while bajo < alto:  # búsqueda binaria: primera columna que llega a `objetivo`
            medio = (bajo + alto) // 2
            if ancho(medio) >= objetivo:
                alto = medio
            else:
                bajo = medio + 1
        if bajo > 0 and (objetivo - ancho(bajo - 1)) < (ancho(bajo) - objetivo):
            return bajo - 1
        return bajo

    # ------------------------------------------------------------------
    # Edición
    # ------------------------------------------------------------------
    def _insertar(self, texto):
        texto = "".join(c for c in texto if c.isprintable())
        if not texto:
            return
        linea = self.lineas[self.cy]
        self.lineas[self.cy] = linea[: self.cx] + texto + linea[self.cx :]
        self.cx += len(texto)
        self._cambio()

    def _enter(self):
        linea = self.lineas[self.cy]
        sangria = linea[: len(linea) - len(linea.lstrip(" "))]  # conserva la sangría
        resto = linea[self.cx :]
        self.lineas[self.cy] = linea[: self.cx]
        self.lineas.insert(self.cy + 1, sangria + resto)
        self.cy += 1
        self.cx = len(sangria)
        self._cambio()

    def _backspace(self):
        if self.cx > 0:
            linea = self.lineas[self.cy]
            self.lineas[self.cy] = linea[: self.cx - 1] + linea[self.cx :]
            self.cx -= 1
        elif self.cy > 0:
            anterior = self.lineas[self.cy - 1]
            self.cx = len(anterior)
            self.lineas[self.cy - 1] = anterior + self.lineas[self.cy]
            del self.lineas[self.cy]
            self.cy -= 1
        else:
            return
        self._cambio()

    def _suprimir(self):
        linea = self.lineas[self.cy]
        if self.cx < len(linea):
            self.lineas[self.cy] = linea[: self.cx] + linea[self.cx + 1 :]
        elif self.cy < len(self.lineas) - 1:
            self.lineas[self.cy] = linea + self.lineas[self.cy + 1]
            del self.lineas[self.cy + 1]
        else:
            return
        self._cambio()

    def _cambio(self):
        self.modificado = True
        self.descarte_pendiente = False
        self.mensaje = ""
        self._ver_cursor()

    # ------------------------------------------------------------------
    # Guardado
    # ------------------------------------------------------------------
    def guardar(self):
        """Guarda solo si el validador (si hay uno) da el visto bueno."""
        texto = "\n".join(self.lineas)
        error = self.validador(texto) if self.validador else None
        if error:
            numero, mensaje = error
            self.cy = min(max(numero - 1, 0), len(self.lineas) - 1)
            self.cx = 0
            self._ver_cursor()
            self._msg(f"Línea {numero}: {mensaje}", COLOR_ERROR)
            return

        try:
            temporal = self.ruta + ".tmp"
            with open(temporal, "w", encoding="utf-8") as f:
                f.write(texto + "\n")
            os.replace(temporal, self.ruta)  # así nunca queda un archivo a medias
        except OSError as e:
            self._msg(f"No se pudo guardar: {e}", COLOR_ERROR)
            return

        self.modificado = False
        self.descarte_pendiente = False
        self._msg("Guardado.", COLOR_OK)

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def evento(self, e):
        """Procesa un evento de pygame. Devuelve True si hay que volver al menú."""
        if e.type == pygame.TEXTINPUT:
            self._insertar(e.text)
        elif e.type == pygame.KEYDOWN:
            return self._tecla(e)
        elif e.type == pygame.MOUSEWHEEL:
            maximo = max(0, len(self.lineas) - self.visibles)
            self.scroll_y = max(0, min(self.scroll_y - e.y * 3, maximo))
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.area_texto.collidepoint(e.pos):
                fila = (e.pos[1] - self.area.y) // self.alto_linea
                self.cy = min(self.scroll_y + fila, len(self.lineas) - 1)
                x = e.pos[0] - self.area_texto.x - 8 + self.scroll_x
                self.cx = self._col_desde_x(self.lineas[self.cy], x)
                self.descarte_pendiente = False
        return False

    def _tecla(self, e):
        k = e.key
        ctrl = e.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)

        if k == pygame.K_ESCAPE:
            if self.modificado and not self.descarte_pendiente:
                self.descarte_pendiente = True
                self._msg(
                    "Hay cambios sin guardar: Ctrl+S guarda, Esc otra vez descarta.",
                    COLOR_ERROR,
                )
                return False
            return True

        if k in (pygame.K_LCTRL, pygame.K_RCTRL, pygame.K_LSHIFT, pygame.K_RSHIFT,
                 pygame.K_LALT, pygame.K_RALT, pygame.K_LMETA, pygame.K_RMETA):
            return False  # tocar solo un modificador no cancela el aviso de descarte

        self.descarte_pendiente = False

        if ctrl and k == pygame.K_s:
            self.guardar()
            return False
        if ctrl and k == pygame.K_HOME:
            self.cy, self.cx = 0, 0
        elif ctrl and k == pygame.K_END:
            self.cy = len(self.lineas) - 1
            self.cx = len(self.lineas[self.cy])
        elif k == pygame.K_LEFT:
            if self.cx > 0:
                self.cx -= 1
            elif self.cy > 0:
                self.cy -= 1
                self.cx = len(self.lineas[self.cy])
        elif k == pygame.K_RIGHT:
            if self.cx < len(self.lineas[self.cy]):
                self.cx += 1
            elif self.cy < len(self.lineas) - 1:
                self.cy += 1
                self.cx = 0
        elif k == pygame.K_UP:
            self.cy = max(0, self.cy - 1)
            self.cx = min(self.cx, len(self.lineas[self.cy]))
        elif k == pygame.K_DOWN:
            self.cy = min(len(self.lineas) - 1, self.cy + 1)
            self.cx = min(self.cx, len(self.lineas[self.cy]))
        elif k == pygame.K_PAGEUP:
            self.cy = max(0, self.cy - self.visibles)
            self.cx = min(self.cx, len(self.lineas[self.cy]))
        elif k == pygame.K_PAGEDOWN:
            self.cy = min(len(self.lineas) - 1, self.cy + self.visibles)
            self.cx = min(self.cx, len(self.lineas[self.cy]))
        elif k == pygame.K_HOME:
            self.cx = 0
        elif k == pygame.K_END:
            self.cx = len(self.lineas[self.cy])
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._enter()
        elif k == pygame.K_BACKSPACE:
            self._backspace()
        elif k == pygame.K_DELETE:
            self._suprimir()
        elif k == pygame.K_TAB:
            self._insertar("  ")
        else:
            return False

        self._ver_cursor()
        return False

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def _dibujar_linea(self, pantalla, linea, y):
        """Dibuja solo la parte visible de la línea (hay líneas larguísimas, como la de beats)."""
        if not linea:
            return
        x = self.area_texto.x + 8 - self.scroll_x
        if len(linea) > 150:
            inicio = max(0, self.scroll_x // self.ancho_char - 5)
            fin = inicio + self.area_texto.width // self.ancho_char + 15
            x += self.fuente.size(linea[:inicio])[0]
            linea = linea[inicio:fin]
            if not linea:
                return
        pantalla.blit(self.fuente.render(linea, True, COLOR_TEXTO), (x, y))

    def dibujar(self, pantalla):
        pantalla.fill(COLOR_FONDO)

        # Barra superior
        ayuda = self.fuente_chica.render("Ctrl+S guardar  ·  Esc volver", True, COLOR_TEXTO_SUAVE)
        pantalla.blit(ayuda, (self.ancho - ayuda.get_width() - 16, 18))
        titulo = self.titulo + (" *" if self.modificado else "")
        titulo = self._recortar(titulo, self.fuente_titulo, self.ancho - ayuda.get_width() - 56)
        pantalla.blit(self.fuente_titulo.render(titulo, True, COLOR_TEXTO), (16, 14))

        # Texto
        pygame.draw.rect(pantalla, COLOR_PANEL, self.area)
        pantalla.set_clip(self.area_texto)
        for i in range(self.visibles):
            n = self.scroll_y + i
            if n >= len(self.lineas):
                break
            y = self.area.y + i * self.alto_linea
            if n == self.cy:
                pygame.draw.rect(
                    pantalla, COLOR_LINEA_ACTUAL,
                    (self.area_texto.x, y, self.area_texto.width, self.alto_linea),
                )
            self._dibujar_linea(pantalla, self.lineas[n], y)

        # Cursor (parpadea)
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            fila = self.cy - self.scroll_y
            if 0 <= fila < self.visibles:
                x = (self.area_texto.x + 8 - self.scroll_x
                     + self.fuente.size(self.lineas[self.cy][: self.cx])[0])
                y = self.area.y + fila * self.alto_linea
                pygame.draw.line(pantalla, COLOR_TEXTO, (x, y + 2), (x, y + self.alto_linea - 2), 2)
        pantalla.set_clip(None)

        # Números de línea
        pygame.draw.rect(
            pantalla, COLOR_GUTTER,
            (self.area.x, self.area.y, self.ancho_gutter, self.area.height),
        )
        for i in range(self.visibles):
            n = self.scroll_y + i
            if n >= len(self.lineas):
                break
            color = COLOR_TEXTO if n == self.cy else COLOR_TEXTO_SUAVE
            num = self.fuente.render(str(n + 1), True, color)
            pantalla.blit(
                num,
                (self.area.x + self.ancho_gutter - 10 - num.get_width(),
                 self.area.y + i * self.alto_linea),
            )

        # Barra inferior
        pos = self.fuente_chica.render(
            f"Línea {self.cy + 1}/{len(self.lineas)}   Col {self.cx + 1}", True, COLOR_TEXTO_SUAVE
        )
        pantalla.blit(pos, (self.ancho - pos.get_width() - 16, self.alto - 26))
        if self.mensaje:
            texto = self._recortar(self.mensaje, self.fuente_chica, self.ancho - pos.get_width() - 48)
            pantalla.blit(self.fuente_chica.render(texto, True, self.color_mensaje), (16, self.alto - 26))