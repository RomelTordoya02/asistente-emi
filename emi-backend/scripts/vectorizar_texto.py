import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from pymongo import MongoClient
from nltk.corpus import stopwords
import nltk
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION")

# Base del proyecto
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Crear la carpeta data si no existe
os.makedirs(DATA_DIR, exist_ok=True)

nltk.download('stopwords')
spanish_stopwords = stopwords.words('spanish')

# Conexión a MongoDB
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]
coleccion = db[MONGODB_COLLECTION]
secciones = list(coleccion.find({}))

# Construir documentos
documentos = [f"{s['titulo']} {s['contenido']}" for s in secciones if s.get('contenido')]

if not documentos:
    raise ValueError("❌ No hay documentos en la base de datos para vectorizar.")

# Vectorizador
vectorizer = TfidfVectorizer(
    stop_words=spanish_stopwords,
    ngram_range=(1, 3),
    max_df=0.9,
    min_df=2,
    lowercase=True
)

tfidf_matrix = vectorizer.fit_transform(documentos)

# Guardar los archivos en data/
with open(os.path.join(DATA_DIR, 'tfidf_vectorizer.pkl'), 'wb') as f:
    pickle.dump(vectorizer, f)

with open(os.path.join(DATA_DIR, 'tfidf_matrix.pkl'), 'wb') as f:
    pickle.dump(tfidf_matrix, f)

print("✅ Vectorización completada y guardada en carpeta 'data'.")
