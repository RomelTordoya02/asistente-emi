from pymongo import MongoClient
import json
from bson.objectid import ObjectId
from dotenv import load_dotenv
import os

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB")
MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION")

# Conectar a MongoDB y cargar las secciones
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]
coleccion = db[MONGODB_COLLECTION]

# Limpiar la colección antes de cargar los datos nuevamente
coleccion.delete_many({})  # Esto elimina todas las entradas anteriores
# Ruta absoluta a la raíz del proyecto
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ruta_json = os.path.join(BASE_DIR, 'data', 'secciones_completas.json')


# Función para cargar datos desde el archivo JSON completo
def cargar_datos_completos(archivo_json):
    try:
        # Abrir y cargar los datos del archivo JSON
        with open(archivo_json, 'r', encoding='utf-8') as f:
            secciones = json.load(f)

        # Insertar las secciones en la base de datos
        for seccion in secciones:
            seccion['_id'] = ObjectId()  # Generar un nuevo ObjectId para cada sección
            coleccion.insert_one(seccion)

        print(f"Datos del archivo {archivo_json} cargados exitosamente en la base de datos.")

    except Exception as e:
        print(f"Error al cargar datos desde {archivo_json}: {e}")


# Cargar datos
cargar_datos_completos(ruta_json)
