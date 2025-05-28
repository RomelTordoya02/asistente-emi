import os
import re
import json

# Obtener la ruta absoluta a la carpeta raíz del proyecto
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Rutas correctas desde cualquier ubicación
RUTA_RAC01 = os.path.join(BASE_DIR, 'data', 'rac01.txt')
RUTA_RAC02 = os.path.join(BASE_DIR, 'data', 'rac02.txt')
RUTA_SALIDA_JSON = os.path.join(BASE_DIR, 'data', 'secciones_completas.json')


def cargar_texto_txt(archivo):
    with open(archivo, 'r', encoding='utf-8') as f:
        return f.read()


def limpiar_texto(texto):
    texto = texto.lower()
    texto = re.sub(r'\n+', ' ', texto)
    texto = re.sub(r'[^\w\sáéíóúüñ]', '', texto)
    return texto


def dividir_en_secciones(texto, documento_nombre):
    secciones = re.split(r'(artículo \d+)', texto, flags=re.IGNORECASE)
    resultados = []

    for i in range(1, len(secciones), 2):
        titulo = secciones[i].strip()
        contenido = secciones[i + 1].strip() if i + 1 < len(secciones) else ""
        if contenido:
            resultados.append({
                "titulo": titulo,
                "contenido": contenido,
                "documento": documento_nombre
            })

    return resultados


def guardar_json(secciones, ruta_salida):
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        json.dump(secciones, f, ensure_ascii=False, indent=2)


# Procesar documentos
texto_rac01 = limpiar_texto(cargar_texto_txt(RUTA_RAC01))
texto_rac02 = limpiar_texto(cargar_texto_txt(RUTA_RAC02))

secciones_rac01 = dividir_en_secciones(texto_rac01, "RAC-01")
secciones_rac02 = dividir_en_secciones(texto_rac02, "RAC-02")

# Unir y guardar en archivo
secciones_totales = secciones_rac01 + secciones_rac02
guardar_json(secciones_totales, RUTA_SALIDA_JSON)

print(f"✅ {len(secciones_totales)} secciones guardadas en {RUTA_SALIDA_JSON}")
