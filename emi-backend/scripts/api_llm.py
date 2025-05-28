import os
import faiss
import pickle
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

modelo = SentenceTransformer("all-MiniLM-L6-v2")
index = faiss.read_index(os.path.join(os.path.dirname(__file__), "../data/indice_faiss.index"))

with open(os.path.join(os.path.dirname(__file__), "../data/metadata_articulos.pkl"), "rb") as f:
    metadata = pickle.load(f)

def buscar_articulo_similar(pregunta, top_k=1):
    embedding = modelo.encode([pregunta])
    _, indices = index.search(np.array(embedding), top_k)
    resultados = [metadata[i] for i in indices[0]]
    return resultados

def consultar_openai(pregunta, contexto):
    mensajes = [
        {
            "role": "system",
            "content": f"""
Eres un asistente experto en reglamentos académicos. 
Responde solo con base en el siguiente artículo del reglamento RAC-01 o RAC-02. 
No inventes información.

TEXTO:
{contexto}
""".strip()
        },
        {
            "role": "user",
            "content": pregunta
        }
    ]

    try:
        respuesta = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=mensajes,
            max_tokens=512,
            temperature=0.3
        )
        return respuesta.choices[0].message.content.strip()
    except Exception as e:
        return f"[ERROR] No se pudo consultar OpenAI: {e}"
def responder_con_faiss_y_openai(pregunta):
    print("🔍 Buscando artículo más relevante en FAISS...")
    resultado = buscar_articulo_similar(pregunta, top_k=1)

    if resultado:
        contexto = f"{resultado[0]['articulo']} - {resultado[0]['titulo']}\n{resultado[0]['contenido']}"
    else:
        contexto = "No se encontró información relevante en el reglamento."

    print("🤖 Consultando OpenAI...")
    return consultar_openai(pregunta, contexto)
