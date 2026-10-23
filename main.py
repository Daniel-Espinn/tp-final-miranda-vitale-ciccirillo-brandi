import pygame
import config as cfg
from pantallas import PantallaMenu, PantallaCargarCanciones, PantallaElegirCancion


class App:
    """Ventana, fuentes y loop principal. Cada pantalla se cambia con cambiar()."""

    def __init__(self):
        pygame.init()
        self.ventana = pygame.display.set_mode((cfg.ANCHO, cfg.ALTO), pygame.RESIZABLE)
        pygame.display.set_caption(cfg.TITULO)
        self.reloj = pygame.time.Clock()

        self.fuente_titulo = pygame.font.Font(None, 64)
        self.fuente = pygame.font.Font(None, 32)
        self.fuente_chica = pygame.font.Font(None, 26)

        self.corriendo = True
        self.actual = None
        self.menu = PantallaMenu(self)  # el menú se crea una vez y se reutiliza
        self.cargar= PantallaCargarCanciones(self)
        self.cambiar(self.menu)
        self.elegir = PantallaElegirCancion(self)


    def cambiar(self, pantalla):
        if self.actual is not None:
            self.actual.al_salir()
        self.actual = pantalla
        pantalla.al_entrar()

    def salir(self):
        self.corriendo = False

    def ejecutar(self):
        while self.corriendo:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    self.salir()
                elif evento.type == pygame.VIDEORESIZE:
                    if self.actual:
                        self.actual.recalcular_layout(evento.w, evento.h)
                elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                    if self.actual:
                        ancho, alto = self.ventana.get_size()
                        self.actual.recalcular_layout(ancho, alto)
                else:
                    self.actual.evento(evento)

            self.actual.actualizar()
            self.actual.dibujar(self.ventana)
            pygame.display.flip()
            self.reloj.tick(cfg.FPS)

        pygame.quit()


def main():
    App().ejecutar()


if __name__ == "__main__":
    main()
