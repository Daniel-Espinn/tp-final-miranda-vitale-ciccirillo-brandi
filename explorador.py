"""Explorador de archivos hecho solo con pygame (sin tkinter). Reutilizable."""

import os

import pygame

import config as cfg


def recortar(texto, fuente, ancho_max):
    """Corta el texto con '...' para que entre en ancho_max píxeles."""
    if fuente.size(texto)[0] <= ancho_max:
        return texto
    while texto and fuente.size(texto + "...")[0] > ancho_max:
        texto = texto[:-1]
    return texto + "..."


class Explorador:
    """
    Muestra carpetas y audios. Clic en una carpeta la abre, clic en una canción
    la marca o desmarca (las marcas se conservan al cambiar de carpeta).

    evento(e) devuelve:
        None        -> sigue abierto
        []          -> canceló
        [rutas...]  -> aceptó (o soltó un archivo en la ventana)
    """

    ALTO_FILA = 30
    COLOR_CARPETA = (140, 170, 255)

    def __init__(self, carpeta_inicial, fuente, fuente_chica,
                 extensiones=None, ancho=cfg.ANCHO):
        self.fuente = fuente
        self.fuente_chica = fuente_chica
        self.ancho = ancho
        self.extensiones = extensiones or cfg.EXTENSIONES

        carpeta = os.path.abspath(carpeta_inicial or "")
        if not os.path.isdir(carpeta):
            carpeta = os.path.expanduser("~")
        self.carpeta = carpeta
        self.seleccion = set()  # rutas completas marcadas

        self.panel = pygame.Rect(40, 110, ancho - 80, 390)
        self.filas_visibles = (self.panel.height - 20) // self.ALTO_FILA
        self.boton_cancelar = pygame.Rect(40, 525, 180, 50)
        self.boton_aceptar = pygame.Rect(ancho - 40 - 260, 525, 260, 50)

        self.entradas = []  # (tipo, nombre); tipo: "subir", "carpeta" o "audio"
        self.scroll = 0
        self.error = ""
        self._listar()

    # --- Carpeta actual ---
    def _listar(self):
        carpetas, audios = [], []
        self.error = ""
        try:
            nombres = os.listdir(self.carpeta)
        except OSError as e:
            self.error = f"No se puede abrir la carpeta: {e.strerror or e}"
            nombres = []

        for nombre in nombres:
            if nombre.startswith("."):
                continue  # ocultos
            ruta = os.path.join(self.carpeta, nombre)
            if os.path.isdir(ruta):
                carpetas.append(nombre)
            elif os.path.splitext(nombre)[1].lower() in self.extensiones:
                audios.append(nombre)

        self.entradas = []
        if os.path.dirname(self.carpeta) != self.carpeta:  # en la raíz no se sube
            self.entradas.append(("subir", ".."))
        self.entradas += [("carpeta", n) for n in sorted(carpetas, key=str.lower)]
        self.entradas += [("audio", n) for n in sorted(audios, key=str.lower)]

    def _ir_a(self, carpeta):
        self.carpeta = carpeta
        self.scroll = 0
        self._listar()

    def _click_entrada(self, indice):
        tipo, nombre = self.entradas[indice]
        if tipo == "subir":
            self._ir_a(os.path.dirname(self.carpeta))
        elif tipo == "carpeta":
            self._ir_a(os.path.join(self.carpeta, nombre))
        else:
            self.seleccion.symmetric_difference_update({os.path.join(self.carpeta, nombre)})

    # --- Eventos ---
    def evento(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                return []
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.seleccion:
                return sorted(self.seleccion)
            elif e.key == pygame.K_BACKSPACE:
                self._ir_a(os.path.dirname(self.carpeta))
        elif e.type == pygame.MOUSEWHEEL:
            maximo = max(0, len(self.entradas) - self.filas_visibles)
            self.scroll = max(0, min(self.scroll - e.y, maximo))
        elif e.type == pygame.DROPFILE:
            return [e.file]
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.boton_cancelar.collidepoint(e.pos):
                return []
            elif self.boton_aceptar.collidepoint(e.pos):
                if self.seleccion:
                    return sorted(self.seleccion)
            elif self.panel.collidepoint(e.pos) and e.pos[1] >= self.panel.y + 12:
                fila = (e.pos[1] - (self.panel.y + 12)) // self.ALTO_FILA
                if fila < self.filas_visibles and self.scroll + fila < len(self.entradas):
                    self._click_entrada(self.scroll + fila)
        return None

    # --- Dibujo ---
    def dibujar(self, s):
        fuente, chica = self.fuente, self.fuente_chica
        s.fill(cfg.COLOR_FONDO)

        s.blit(fuente.render("Elegí una o más canciones", True, cfg.COLOR_TEXTO), (40, 28))
        ayuda = chica.render("Retroceso: subir · Esc: cancelar", True, cfg.COLOR_TEXTO_SUAVE)
        s.blit(ayuda, (self.ancho - 40 - ayuda.get_width(), 34))

        ruta = recortar(self.carpeta, chica, self.ancho - 80)
        s.blit(chica.render(ruta, True, cfg.COLOR_TEXTO_SUAVE), (40, 76))

        pygame.draw.rect(s, cfg.COLOR_PANEL, self.panel, border_radius=10)
        pos = pygame.mouse.get_pos()

        visibles = self.entradas[self.scroll:self.scroll + self.filas_visibles]
        for i, (tipo, nombre) in enumerate(visibles):
            y = self.panel.y + 12 + i * self.ALTO_FILA
            fila = pygame.Rect(self.panel.x + 6, y - 3, self.panel.width - 12, self.ALTO_FILA - 2)
            if fila.collidepoint(pos):
                pygame.draw.rect(s, cfg.COLOR_FILA_HOVER, fila, border_radius=6)

            x_texto = self.panel.x + 15
            if tipo == "subir":
                texto, color = ".. (subir)", cfg.COLOR_TEXTO_SUAVE
            elif tipo == "carpeta":
                texto, color = nombre + "/", self.COLOR_CARPETA
            else:
                marcada = os.path.join(self.carpeta, nombre) in self.seleccion
                caja = pygame.Rect(x_texto, y + 2, 16, 16)
                pygame.draw.rect(s, cfg.COLOR_TEXTO_SUAVE, caja, width=2, border_radius=3)
                if marcada:
                    pygame.draw.rect(s, cfg.COLOR_OK, caja.inflate(-6, -6), border_radius=2)
                x_texto += 28
                texto, color = nombre, (cfg.COLOR_OK if marcada else cfg.COLOR_TEXTO)

            texto = recortar(texto, chica, self.panel.right - 15 - x_texto)
            s.blit(chica.render(texto, True, color), (x_texto, y))

        if not any(tipo != "subir" for tipo, _ in self.entradas):
            aviso = self.error or "No hay carpetas ni canciones acá."
            color = cfg.COLOR_ERROR if self.error else cfg.COLOR_TEXTO_SUAVE
            txt = chica.render(recortar(aviso, chica, self.panel.width - 40), True, color)
            s.blit(txt, txt.get_rect(center=self.panel.center))

        # Botones
        color = cfg.COLOR_BOTON_HOVER if self.boton_cancelar.collidepoint(pos) else cfg.COLOR_BOTON
        pygame.draw.rect(s, color, self.boton_cancelar, border_radius=12)
        txt = fuente.render("Cancelar", True, cfg.COLOR_TEXTO)
        s.blit(txt, txt.get_rect(center=self.boton_cancelar.center))

        n = len(self.seleccion)
        if n:
            color = cfg.COLOR_BOTON_HOVER if self.boton_aceptar.collidepoint(pos) else cfg.COLOR_BOTON
            color_txt, etiqueta = cfg.COLOR_TEXTO, f"Añadir ({n})"
        else:
            color, color_txt, etiqueta = (40, 40, 65), cfg.COLOR_TEXTO_SUAVE, "Añadir"
        pygame.draw.rect(s, color, self.boton_aceptar, border_radius=12)
        txt = fuente.render(etiqueta, True, color_txt)
        s.blit(txt, txt.get_rect(center=self.boton_aceptar.center))