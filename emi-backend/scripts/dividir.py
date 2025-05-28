import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

# Cargar modelo y recursos
modelo = SentenceTransformer("all-MiniLM-L6-v2")
index = faiss.read_index("../data/indice_faiss.index")
with open("../data/metadata_articulos.pkl", "rb") as f:
    metadata = pickle.load(f)

# Función para buscar el artículo más relevante
def buscar_articulo_similar(pregunta, top_k=1):
    embedding = modelo.encode([pregunta])
    _, indices = index.search(np.array(embedding), top_k)
    resultados = [metadata[i] for i in indices[0]]
    return resultados

if __name__ == "__main__":
    pregunta = "qué tipos de permisos hay"
    resultados = buscar_articulo_similar(pregunta)
    for r in resultados:
        print(f"🔹 {r['articulo']} - {r['titulo']}\n{r['contenido']}\n")
