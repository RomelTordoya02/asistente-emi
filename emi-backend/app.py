from flask import Flask, request, jsonify
from flask_cors import CORS
from modelo_consulta import ModeloConsultaEMI
from dotenv import load_dotenv
import os
from scripts.api_llm import consultar_openai

# Cargar variables de entorno
load_dotenv()

# Inicializar Flask
app = Flask(__name__)

# Habilitar CORS para permitir conexión desde frontend
CORS(app)

# Instancia del modelo
modelo = ModeloConsultaEMI()


@app.route("/")
def home():
    return jsonify({"mensaje": "API del Asistente EMI funcionando 🚀"})


@app.route("/api/preguntar", methods=["POST"])
def preguntar():
    data = request.get_json()
    pregunta = data.get("pregunta")
    contexto = data.get("contexto", "")

    if not pregunta:
        return jsonify({"error": "Debes enviar una pregunta"}), 400

    try:
        respuesta = modelo.generar_respuesta(pregunta, contexto)
        return jsonify({"respuesta": respuesta})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
