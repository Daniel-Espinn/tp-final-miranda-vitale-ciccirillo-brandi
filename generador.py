"""Generación de charts con autochart en un hilo aparte (para no congelar la ventana)."""

import os
import threading
import traceback

import config as cfg
from canciones import guardar_chart, quitar_cancion


class Generador:
    def __init__(self, nombres):
        self.nombres = list(nombres)
        self._lock = threading.Lock()
        self._estado = {
            "fraccion": 0.0,
            "texto": "Iniciando...",
            "nombre": self.nombres[0] if self.nombres else "",
            "indice": 0,
            "total": len(self.nombres),
            "ok": [],
            "errores": [],
            "terminado": False,
        }

    def iniciar(self):
        threading.Thread(target=self._trabajo, daemon=True).start()

    def estado(self):
        """Copia del estado actual (seguro de leer desde el hilo principal)."""
        with self._lock:
            copia = dict(self._estado)
            copia["ok"] = list(copia["ok"])
            copia["errores"] = list(copia["errores"])
            return copia

    def _actualizar(self, **cambios):
        with self._lock:
            self._estado.update(cambios)

    def _reportar(self, fraccion, texto):
        """Callback que autochart llama a medida que avanza."""
        self._actualizar(fraccion=fraccion, texto=texto)
        print(f"{fraccion*100:.0f}% - {texto}")

    def _trabajo(self):
        self._actualizar(texto="Cargando autochart...")

        try:
            import autochart  # se importa acá para que la ventana abra rápido
        except Exception as e:
            for nombre in self.nombres:
                quitar_cancion(nombre)
            self._actualizar(errores=[f"No se pudo importar autochart: {e}"], terminado=True)
            return

        for i, nombre in enumerate(self.nombres):
            self._actualizar(indice=i, nombre=nombre, fraccion=0.0, texto="Empezando...")
            try:
                resultado = autochart.generar(
                    os.path.join(cfg.CARPETA_CANCIONES, nombre), progreso=self._reportar
                )
                guardar_chart(resultado, nombre)
                with self._lock:
                    self._estado["ok"].append(nombre)
            except Exception as e:
                traceback.print_exc()  # el detalle completo queda en la consola
                quitar_cancion(nombre)  # así se puede volver a intentar
                with self._lock:
                    self._estado["errores"].append(f"{nombre}: {e}")

        self._actualizar(fraccion=1.0, terminado=True)