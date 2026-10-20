import os

import pygame

import canciones
import config as cfg
from formato_chart import leer_chart

import pygame


nombre_cancion= "Zara Larsson - Midnight Sun (Official Music Video).mp3"
notas = leer_chart(canciones.ruta_chart(nombre_cancion))["notas"]
teclas= {pygame.K_a: 0, pygame.K_s:1, pygame.K_d:2, pygame.K_f:3, pygame.K_g:4}
tiempo_caida= 1.5

pygame.init() #inicia todas las cosas de pygame 
pantalla = pygame.display.set_mode((1000,700))
reloj = pygame.time.Clock()
analizadas=[]
pygame.mixer.music.load("canciones/" + nombre_cancion)
pygame.mixer.music.play()
inicio= pygame.time.get_ticks()

#------------------------------------------------------------------------------------------------------
colores = [(0, 200, 0), (220, 50, 50), (240, 200, 0), (50, 130, 230), (240, 130, 0)]  # verde, rojo, amarillo, azul, naranja
ancho_carril = 100
x0 = (pantalla.get_width() - 5 * ancho_carril) // 2   # centra los carriles
y_linea = pantalla.get_height() - 150                  # altura de la línea de golpe    
#------------------------------------------------------------------------------




corriendo = True
while corriendo:
    segundos = (pygame.time.get_ticks() - inicio) / 1000
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            corriendo = False
        elif evento.type == pygame.KEYDOWN:
            if evento.key in teclas:
                carril_apretado= teclas[evento.key]
                nota_cercana = None
                distancia_nota_cercana= 1000000000000
                for i in range(len(notas)):
                    tiempo, carril, duracion= notas[i]
                    if (carril == carril_apretado) and (i not in analizadas):
                        diferencia = ((tiempo-segundos)**2)**0.5
                        if diferencia < distancia_nota_cercana:
                            nota_cercana = i
                            distancia_nota_cercana= diferencia
                if distancia_nota_cercana <= 0.1:
                    analizadas.append(nota_cercana)
                    if distancia_nota_cercana <=0.05:
                        print("perfecto")
                    else:
                        print("bien")
                else:
                    print("Mal")


    for i in range(len(notas)):
        tiempo, carril, duracion = notas[i]
        if (i not in analizadas) and (segundos - tiempo > 0.1):
            analizadas.append(i)
            print("Fallada")


    pantalla.fill((100, 100, 100))   

    for i in range(len(notas)):
        tiempo, carril, duracion = notas[i]
        tiempo_falatante_nota = tiempo - segundos
        if -0.2 <= tiempo_falatante_nota <= tiempo_caida:
            porcentaje = (1 - tiempo_falatante_nota / tiempo_caida)*100
            y = int(y_linea * porcentaje / 100)
            x = x0 + carril * ancho_carril + ancho_carril // 2 - 2
            if duracion > 0:
                alto = int(duracion / tiempo_caida * y_linea)
                pygame.draw.rect(pantalla, colores[carril], (x - 8, y - alto, 16, alto))
            pygame.draw.circle(pantalla, colores[carril], (x, y), 20)


#---------------------------------------------------------------------------------------------
    for i, color in enumerate(colores):
        x = x0 + i * ancho_carril
        pygame.draw.rect(pantalla, color, (x, 0, ancho_carril - 4, pantalla.get_height()), 2)
    pygame.draw.line(pantalla, (255, 255, 255), (x0, y_linea), (x0 + 5 * ancho_carril, y_linea), 3)
#------------------------------------------------------------------------------------------------------

    pygame.display.flip()
    reloj.tick(60)

pygame.quit()