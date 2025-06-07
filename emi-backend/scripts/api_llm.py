import os
import faiss
import pickle
import numpy as np
import unicodedata
import re
from openai import OpenAI
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# Cargar variables de entorno
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Modelo de embeddings
modelo = SentenceTransformer("all-MiniLM-L6-v2")

# Cargar índice FAISS y metadatos
base_dir = os.path.dirname(__file__)
index = faiss.read_index(os.path.join(base_dir, "../data/indice_faiss.index"))

with open(os.path.join(base_dir, "../data/metadata_articulos.pkl"), "rb") as f:
    metadata = pickle.load(f)

# 🔤 Función para normalizar texto (elimina tildes, signos raros, y pasa todo a minúsculas)
def normalizar_texto(texto):
    texto = texto.lower()
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    texto = re.sub(r"[^a-z0-9\s]", "", texto)
    return texto.strip()

# 🔍 Buscar artículos similares usando FAISS y texto normalizado
def buscar_articulo_similar(pregunta, top_k=10):
    pregunta_normalizada = normalizar_texto(pregunta)
    embedding = modelo.encode([pregunta_normalizada])
    _, indices = index.search(np.array(embedding), top_k)
    resultados = [metadata[i] for i in indices[0]]
    return [r for r in resultados if len(r.get("contenido", "").strip()) > 30]

# 💬 Consultar a OpenAI con los artículos relevantes como contexto
def consultar_openai(pregunta, contexto):
    mensajes = [
        {
            "role": "system",
            "content": f"""
Eres un asistente académico especializado en los reglamentos RAC-01 y RAC-02 de la Escuela Militar de Ingeniería.

Tu única fuente de información debe ser el siguiente contenido textual extraído directamente de los reglamentos. Debes responder de manera clara, completa y en estilo conversacional, citando literalmente lo que corresponda.

⚠️ Si no encuentras la respuesta en el contexto proporcionado, responde exactamente: “No se especifica en estos artículos del reglamento.”

📄 Fragmentos del reglamento:
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
            max_tokens=1024,
            temperature=0.2
        )
        return respuesta.choices[0].message.content.strip()
    except Exception as e:
        return f"[ERROR] No se pudo consultar OpenAI: {e}"

# 🔁 Función principal que responde usando embeddings + contexto + OpenAI
def responder_con_faiss_y_openai(pregunta):
    print("🔍 Buscando artículos más relevantes en FAISS...")
    articulos_utiles = buscar_articulo_similar(pregunta, top_k=10)

    # Si no encuentra, intentar buscar con palabras clave manuales
    if not articulos_utiles:
        claves = ["admisión", "permisos", "derechos", "obligaciones", "inasistencia", "evaluación", "estudiante militar"]
        for clave in claves:
            if clave in normalizar_texto(pregunta):
                print(f"🔁 Reintentando búsqueda con palabra clave: {clave}")
                articulos_utiles = buscar_articulo_similar(clave, top_k=10)
                break

    if not articulos_utiles:
        return "No se encontró información suficiente en los artículos del reglamento para responder esta pregunta."

    contexto = "\n\n".join([
        f"[{art.get('rac', 'RAC-?')}] {art.get('articulo', '')} - {art.get('titulo', '')}\n{art.get('contenido', '').strip()}"
        for art in articulos_utiles
    ])

    print("🤖 Consultando OpenAI con contexto relevante...")
    print("📄 Pregunta:", pregunta)
    print("📄 Fragmento del contexto:\n", contexto[:500], "...")

    return consultar_openai(pregunta, contexto)
