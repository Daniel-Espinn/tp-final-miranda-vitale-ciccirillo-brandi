import autochart

def mostrar_avance(fraccion, texto):
    
    print(f"{fraccion * 100:.0f}% - {texto}")

resultado = autochart.generar("canciones/Rock nacional/Amor_amarillo.wav")

print(resultado.beats[:6])
for nota in resultado.notas["experto"][:6]:
    print(nota)