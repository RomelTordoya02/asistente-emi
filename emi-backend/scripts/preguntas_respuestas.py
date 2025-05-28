import os
import json
import re

# Ruta base del proyecto
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Cargar los artículos previamente extraídos
with open(os.path.join(DATA_DIR, 'rac01_articulos.json'), "r", encoding="utf-8") as f:
    rac01 = json.load(f)

with open(os.path.join(DATA_DIR, 'rac02_articulos.json'), "r", encoding="utf-8") as f:
    rac02 = json.load(f)


def extraer_numero_articulo(titulo):
    match = re.search(r'\d+', titulo)
    return int(match.group(0)) if match else float('inf')


def generar_pregunta_respuesta(articulo, documento):
    numero = extraer_numero_articulo(articulo['titulo'])

    preguntas = [
        f"¿Cuál es el propósito del artículo {numero} del {documento}?",
        f"Explica detalladamente el contenido del artículo {numero} del {documento}.",
        f"¿Qué aspectos fundamentales se establecen en el artículo {numero} del {documento}?",
        f"Resume los puntos clave del artículo {numero} del {documento}.",
        f"¿Cómo se aplica lo establecido en el artículo {numero} del {documento}?"
    ]

    def generar_respuesta_completa(contexto):
        parrafos = re.split(r'\n+', contexto)
        contexto_ampliado = ' '.join(parrafos[:3]) if len(parrafos) > 1 else contexto
        return (
            f"Según el artículo {numero} del {documento}, "
            f"{contexto_ampliado} "
            f"Este artículo es fundamental porque establece lineamientos específicos "
            f"para la aplicación de la normativa en el contexto de {documento}."
        )

    return [
        {
            "pregunta": pregunta,
            "contexto": articulo["contenido"],
            "respuesta": generar_respuesta_completa(articulo["contenido"])
        }
        for pregunta in preguntas
    ]


def ordenar_articulos(articulos):
    return sorted(articulos, key=lambda x: extraer_numero_articulo(x['titulo']))


# Generar dataset
dataset = []

# Procesar RAC-01 y RAC-02 ordenados
rac01_ordenado = ordenar_articulos(rac01)
rac02_ordenado = ordenar_articulos(rac02)

for articulo in rac01_ordenado:
    dataset.extend(generar_pregunta_respuesta(articulo, "RAC-01"))

for articulo in rac02_ordenado:
    dataset.extend(generar_pregunta_respuesta(articulo, "RAC-02"))

# Guardar dataset en JSON
with open(os.path.join(DATA_DIR, 'dataset_entrenamiento.json'), "w", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

print(f"✅ Dataset generado con {len(dataset)} ejemplos explicativos y guardado como dataset_entrenamiento.json")
print(f"Ejemplos de RAC-01: {len([d for d in dataset if 'RAC-01' in d['respuesta']])}")
print(f"Ejemplos de RAC-02: {len([d for d in dataset if 'RAC-02' in d['respuesta']])}")
