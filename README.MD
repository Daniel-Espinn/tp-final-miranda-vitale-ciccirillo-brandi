# TP FINAL - Pensamiento Computacional - 2026
## UdeSA

### Integrantes

- Daniel Agustín Miranda Espin
- Isabella Tina Vitale
- Lorenzo Ciccirillo Kuz
- Pedro Brandi 

### Resumen del juego
El juego es un "rhythm game" inspirado en guitar hero. Nos movimos a una estética pixel art y añadimos un modo historia muy simple.

### Resumen del desarrollo

#### Estructura de archivos
Lo que hago es comenzar con las carpetas
canciones y charts
En canciones almacenamos las canciones del usuario en sus respectivas carpetas.
En charts se almacenan los archivos de texto que fueron generados por Autochart


```
.
├── añadir_canciones.py
├── autochart
│   ├── api.py
│   ├── __init__.py
│   ├── modelo.py
│   ├── modelos
│   ├── __pycache__
│   └── tipos.py
├── canciones
│   └── Zara Larsson - Midnight Sun (Official Music Video).mp3
├── canciones.py
├── charts
│   ├── canciones.txt
│   └── Zara Larsson - Midnight Sun (Official Music Video).mp3.txt
├── config.py
├── editor_texto.py
├── explorador.py
├── formato_chart.py
├── generador.py
├── juego.py
├── main.py
├── pantallas.py
├── prueba_ventana.py
```

#### Diseño

Como elegimos una estética pixel art. Al escalar imágenes, usamos pygame.transform.scale() en lugar de smoothscale() para que los bordes queden definidos y cuadrados.

### Detalles técnicos
Para comenzar el menu fue creado en su totalidad con pygame.
En el menu usamos la clase Pantalla que heredan todas las pantallas el principal "PantallaMenu" con el menu principal del juego. Creamos un bucle for para generar los botones (y no repetir codigo). Cada click es detectado en la funcion "_clic" donde usamos el metodo app.cambiar

### Problemáticas