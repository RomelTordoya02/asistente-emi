import os
import json
import re
from typing import List, Dict

# Definir rutas relativas basadas en la ubicación de este script
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')


def generar_variantes_preguntas(pregunta_base: str) -> List[str]:
    """
    Genera variantes de preguntas para aumentar la diversidad del dataset
    """
    variantes = [
        pregunta_base,
        f"¿Podrías explicarme más sobre {pregunta_base}?",
        f"Dame más detalles de {pregunta_base}",
        f"Explícame en profundidad {pregunta_base}",
        f"Necesito comprender completamente {pregunta_base}"
    ]
    return variantes


def enriquecer_contexto(contexto: str) -> str:
    """
    Añade contexto y ejemplos para enriquecer la información
    """
    contexto_ampliado = contexto + "\n\n" + """
    Ejemplo de aplicación:
    - Este artículo es fundamental para comprender los procedimientos administrativos
    - Proporciona un marco legal y normativo claro
    - Sirve como guía para estudiantes y personal administrativo
    """
    return contexto_ampliado


def procesar_dataset(ruta_dataset: str) -> List[Dict]:
    """
    Procesa y enriquece el dataset existente
    """
    with open(ruta_dataset, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    dataset_enriquecido = []

    for entrada in dataset:
        # Generar variantes de preguntas
        variantes_preguntas = generar_variantes_preguntas(entrada['pregunta'])

        # Enriquecer cada variante
        for variante in variantes_preguntas:
            nueva_entrada = {
                'pregunta': variante,
                'contexto': enriquecer_contexto(entrada['contexto']),
                'respuesta': entrada['respuesta']
            }
            dataset_enriquecido.append(nueva_entrada)

    return dataset_enriquecido


# Uso: definir la ruta del dataset utilizando DATA_DIR
ruta_dataset = os.path.join(DATA_DIR, 'dataset_entrenamiento.json')
dataset_final = procesar_dataset(ruta_dataset)

# Guardar dataset enriquecido usando rutas relativas
with open(os.path.join(DATA_DIR, 'dataset_entrenamiento_enriquecido.json'), 'w', encoding='utf-8') as f:
    json.dump(dataset_final, f, ensure_ascii=False, indent=2)

print(f"✅ Dataset enriquecido generado con {len(dataset_final)} entradas")
