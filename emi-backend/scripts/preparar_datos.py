import os
import json
import re

# Ruta absoluta a la raíz del proyecto
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Cargar los textos de RAC-01 y RAC-02
with open(os.path.join(DATA_DIR, 'rac01.txt'), "r", encoding="utf-8") as f:
    texto_rac01 = f.read()

with open(os.path.join(DATA_DIR, 'rac02.txt'), "r", encoding="utf-8") as f:
    texto_rac02 = f.read()


def extraer_articulos(texto):
    pattern = r'(art[íi]culo\s*\d+)[:\s]*(.*?)(?=art[ íi]culo\s*\d+|$)'
    matches = re.findall(pattern, texto, re.DOTALL | re.IGNORECASE)

    articulos = []
    for titulo, contenido in matches:
        contenido = re.sub(r'\s+', ' ', contenido.strip())
        if contenido:
            articulos.append({
                "titulo": titulo.lower(),
                "contenido": contenido
            })

    return articulos


# Extraer artículos
articulos_rac01 = extraer_articulos(texto_rac01)
articulos_rac02 = extraer_articulos(texto_rac02)

# Guardar en archivos JSON
with open(os.path.join(DATA_DIR, 'rac01_articulos.json'), "w", encoding="utf-8") as f:
    json.dump(articulos_rac01, f, ensure_ascii=False, indent=2)

with open(os.path.join(DATA_DIR, 'rac02_articulos.json'), "w", encoding="utf-8") as f:
    json.dump(articulos_rac02, f, ensure_ascii=False, indent=2)

print(f"✅ Artículos extraídos: RAC-01: {len(articulos_rac01)}, RAC-02: {len(articulos_rac02)}")
