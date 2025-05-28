import os
import sys
import json
import re
import difflib
import unicodedata
from typing import List, Dict
from dotenv import load_dotenv
from num2words import num2words  # Instalar con: pip install num2words
from scripts.api_llm import consultar_openai
from scripts.api_llm import responder_con_faiss_y_openai
from typing import List, Dict





def ordinal_es(n: int) -> str:
    """Convierte un número en su forma ordinal en español de forma dinámica."""
    return num2words(n, lang='es', to='ordinal')


def quitar_acentos(texto: str) -> str:
    """Elimina acentos del texto para una comparación insensible a ellos."""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


# Cargar variables de entorno desde .env
load_dotenv()

# Ruta base del proyecto
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
CHECKPOINTS_DIR = os.path.join(BASE_DIR, 'checkpoints_emi')

try:
    from transformers import (
        AutoTokenizer,
        AutoModelForSeq2SeqLM,
        Trainer,
        TrainingArguments,
        DataCollatorForSeq2Seq
    )
    from datasets import Dataset

    try:
        from peft import LoraConfig, get_peft_model, PeftModel

        PEFT_DISPONIBLE = True
    except ImportError:
        print("🚫 PEFT no disponible. Usando método de fine-tuning estándar.")
        PEFT_DISPONIBLE = False

except ImportError as e:
    print(f"❌ Error de importación: {e}")
    print("Por favor, instala las librerías con: pip install transformers datasets pandas accelerate peft")
    sys.exit(1)


class ModeloConsultaEMI:
    def __init__(self):
        self.modelo_base = os.getenv("MODELO_BASE")
        self.directorio_checkpoints = CHECKPOINTS_DIR
        self.ruta_dataset = os.path.join(DATA_DIR, 'dataset_entrenamiento_enriquecido.json')

        os.makedirs(self.directorio_checkpoints, exist_ok=True)
        self.dir_modelo_base = os.path.join(self.directorio_checkpoints, 'modelo_base')
        self.dir_modelo_fine_tuned = os.path.join(self.directorio_checkpoints, 'modelo_fine_tuned')
        os.makedirs(self.dir_modelo_base, exist_ok=True)
        os.makedirs(self.dir_modelo_fine_tuned, exist_ok=True)

        # La memoria de conversación guarda:
        #   - 'ultimo_articulo': número de artículo buscado.
        #   - 'ultimo_rac': RAC buscado (si se especificó).
        #   - 'sugerencias_previas': lista de objetos con:
        #         'display': cadena para mostrar (ej. "Artículo 40 del RAC-1").
        #         'respuesta': texto completo de la respuesta.
        self.contexto_conversacion = {
            'ultima_consulta': None,
            'ultimo_articulo': None,
            'ultimo_rac': None,
            'sugerencias_previas': []
        }

        self.cargar_dataset_completo()
        self._inicializar_modelo()

    # Funciones auxiliares para respuestas formales
    def es_saludo(self, texto: str) -> bool:
        saludos = ["hola", "buenos dias", "buenas tardes", "buenas noches", "saludos", "que tal", "como estas"]
        texto = quitar_acentos(texto)
        return any(s in texto for s in saludos)

    def es_agradecimiento(self, texto: str) -> bool:
        agradecimientos = ["gracias", "muchas gracias", "te lo agradezco", "agradecido", "agradecida"]
        texto = quitar_acentos(texto)
        return any(a in texto for a in agradecimientos)

    def es_despedida(self, texto: str) -> bool:
        despedidas = ["chau", "hasta luego", "adios", "nos vemos", "bye"]
        texto = quitar_acentos(texto)
        return any(d in texto for d in despedidas)

    def cargar_dataset_completo(self):
        try:
            with open(self.ruta_dataset, 'r', encoding='utf-8') as f:
                self.dataset_completo = json.load(f)
                self.racs_disponibles = sorted(list(set(
                    re.findall(r'\brac[- :]?0?(\d+)(?!\d)',
                               ' '.join([(entrada.get('contexto', '') + " " + entrada.get('respuesta', '')).lower()
                                         for entrada in self.dataset_completo])
                               )
                )))
                print(f"DEBUG: RACs disponibles: {self.racs_disponibles}")
        except FileNotFoundError:
            print("⚠️ Dataset no encontrado. Iniciando con dataset vacío.")
            self.dataset_completo = []
            self.racs_disponibles = []

    def obtener_articulos_disponibles(self, numero_articulo: str, rac_solicitado: str = None) -> List[Dict]:
        suggestions = {}
        for entrada in self.dataset_completo:
            texto_entrada = (entrada.get('contexto', '') + " " + entrada.get('respuesta', '')).lower()
            arts = re.findall(r'\bart[ií]culo\s*0?(\d+)(?!\d)', texto_entrada)
            if numero_articulo in arts:
                racs = re.findall(r'\brac[- :]?0?(\d+)(?!\d)', texto_entrada)
                if rac_solicitado and rac_solicitado not in racs:
                    continue
                key = (numero_articulo, racs[0] if racs else "desconocido")
                if key not in suggestions:
                    suggestions[key] = {
                        'display': f"Artículo {numero_articulo} del RAC-{key[1]}",
                        'respuesta': entrada['respuesta']
                    }
        return list(suggestions.values())

    def obtener_sugerencias_fuzzy(self, numero_articulo: str, rac_solicitado: str = None) -> List[Dict]:
        suggestions = {}
        for entrada in self.dataset_completo:
            texto_entrada = (entrada.get('contexto', '') + " " + entrada.get('respuesta', '')).lower()
            arts = re.findall(r'\bart[ií]culo\s*0?(\d+)(?!\d)', texto_entrada)
            if rac_solicitado:
                racs = re.findall(r'\brac[- :]?0?(\d+)(?!\d)', texto_entrada)
                if rac_solicitado not in racs:
                    continue
            for art in arts:
                similarity = difflib.SequenceMatcher(None, numero_articulo, art).ratio()
                if similarity >= 0.6 and art != numero_articulo:
                    racs = re.findall(r'\brac[- :]?0?(\d+)(?!\d)', texto_entrada)
                    candidate_rac = racs[0] if racs else "desconocido"
                    key = (art, candidate_rac)
                    if key not in suggestions:
                        suggestions[key] = {
                            'display': f"Artículo {art} del RAC-{candidate_rac}",
                            'respuesta': entrada['respuesta'],
                            'similarity': similarity
                        }
        sorted_suggestions = sorted(suggestions.values(), key=lambda x: x['similarity'], reverse=True)
        return sorted_suggestions

    def generar_respuesta(self, pregunta: str, contexto: str = "") -> str:
        # Quitamos acentos para que la comparación sea insensible
        pregunta_limpia = quitar_acentos(pregunta.lower().strip())
        print(f"DEBUG: Pregunta procesada: {pregunta_limpia}")

        # Si la consulta contiene "artículo", reiniciamos la memoria (nuevo query)
        if re.search(r'\barticulo', pregunta_limpia):
            self.contexto_conversacion = {
                'ultima_consulta': None,
                'ultimo_articulo': None,
                'ultimo_rac': None,
                'sugerencias_previas': []
            }

        # Responder saludos, agradecimientos y despedidas si NO se menciona "artículo" ni "rac"
        if not re.search(r'\barticulo', pregunta_limpia) and not re.search(r'\brac', pregunta_limpia):
            if self.es_saludo(pregunta_limpia):
                return "Hola, mucho gusto. Estoy bien y listo para ayudarte. ¿En qué puedo colaborar?"
            if self.es_agradecimiento(pregunta_limpia):
                return "¡De nada! Me alegra poder ayudarte."
            if self.es_despedida(pregunta_limpia):
                return "¡Hasta luego! Espero haber sido de ayuda."

        if self.manejar_memoria_conversacional(pregunta_limpia):
            return self.responder_desde_memoria(pregunta_limpia)

        articulo_match = re.search(r'\barticulo\s*0?(\d+)(?!\d)', pregunta_limpia)
        rac_match = re.search(r'\brac[- :]?0?(\d+)(?!\d)', pregunta_limpia)
        numero_articulo = articulo_match.group(1) if articulo_match else None
        rac_especifico = rac_match.group(1) if rac_match else None

        print(f"DEBUG: Artículo extraído: {numero_articulo}, RAC extraído: {rac_especifico}")
        print(f"DEBUG: RACs disponibles: {self.racs_disponibles}")

        if numero_articulo:
            if rac_especifico and rac_especifico not in self.racs_disponibles:
                sugerencias = self.obtener_articulos_disponibles(numero_articulo)
                if sugerencias:
                    respuesta = (
                            f"❌ Lo siento, solo tengo información para RAC-{', RAC-'.join(self.racs_disponibles)}. "
                            f"El RAC-{rac_especifico} no está en mi base de conocimientos.\n\n"
                            "🔍 Artículos similares encontrados:\n" +
                            "\n".join([s['display'] for s in sugerencias])
                    )
                else:
                    respuesta = (
                        f"❌ No se encontró información para el Artículo {numero_articulo} "
                        f"en el RAC-{rac_especifico} ni en los RACs disponibles."
                    )
                self.contexto_conversacion['sugerencias_previas'] = sugerencias
                print("DEBUG: Validación RAC fallida, retornando error.")
                return respuesta

            exact_suggestions = {}
            for entrada in self.dataset_completo:
                texto_entrada = quitar_acentos(
                    (entrada.get('contexto', '') + " " + entrada.get('respuesta', '')).lower())
                arts = re.findall(r'\barticulo\s*0?(\d+)(?!\d)', texto_entrada)
                if numero_articulo in arts:
                    racs = re.findall(r'\brac[- :]?0?(\d+)(?!\d)', texto_entrada)
                    print(f"DEBUG: Entrada: {texto_entrada}")
                    print(f"DEBUG: Artículos encontrados: {arts}, RACS encontrados: {racs}")
                    if not rac_especifico:
                        for r in set(racs):
                            key = (numero_articulo, r)
                            if key not in exact_suggestions:
                                exact_suggestions[key] = {
                                    'display': f"Artículo {numero_articulo} del RAC-{r}",
                                    'respuesta': entrada['respuesta']
                                }
                    else:
                        if rac_especifico in racs:
                            key = (numero_articulo, rac_especifico)
                            if key not in exact_suggestions:
                                exact_suggestions[key] = {
                                    'display': f"Artículo {numero_articulo} del RAC-{rac_especifico}",
                                    'respuesta': entrada['respuesta']
                                }
            exact_suggestions = list(exact_suggestions.values())
            if not exact_suggestions:
                fuzzy_suggestions = self.obtener_sugerencias_fuzzy(numero_articulo, rac_especifico)
                if fuzzy_suggestions:
                    respuesta = "🤔 No encontré ese artículo exacto. Quizás buscas:\n" + "\n".join(
                        [s['display'] for s in fuzzy_suggestions])
                    self.contexto_conversacion['sugerencias_previas'] = fuzzy_suggestions
                    print("DEBUG: No se encontró coincidencia exacta, retornando sugerencias fuzzy.")
                    return respuesta
                else:
                    respuesta = (
                        f"❌ No se encontró ningún artículo con el número {numero_articulo} "
                        f"{'en el RAC-' + rac_especifico if rac_especifico else ''}."
                    )
                    print("DEBUG: No se encontró ninguna sugerencia fuzzy.")
                    return respuesta

            self.contexto_conversacion.update({
                'ultima_consulta': pregunta_limpia,
                'ultimo_articulo': numero_articulo,
                'ultimo_rac': rac_especifico,
                'sugerencias_previas': exact_suggestions
            })
            print("DEBUG: Artículo encontrado, almacenando contexto y opciones.")
            if len(exact_suggestions) == 1:
                return exact_suggestions[0]['respuesta']
            else:
                response = f"Se encontraron varias opciones para el artículo {numero_articulo}:\n"
                for i, s in enumerate(exact_suggestions, start=1):
                    response += f"{i}. {s['display']}\n"
                response += "Por favor, indica la opción deseada (por ejemplo, 'dime el primero' o 'del rac 1')."
                return response

        coincidencias = self.buscar_coincidencias(pregunta)
        if coincidencias:
            mejor_coincidencia = coincidencias[0]
            return mejor_coincidencia['datos']['respuesta']

        # Si no encuentra respuesta en MongoDB o búsqueda local
        try:
            print("📄 No se encontró coincidencia exacta. Buscando en archivos de reglamento...")
            return responder_con_faiss_y_openai(pregunta)
        except Exception as e:
            print(f"❌ Error al consultar OpenAI con archivos TXT: {e}")
            return "🤖 Lo siento, no encontré una respuesta en el sistema y ocurrió un error al consultar los archivos de reglamento."
        return (
            "🤔 Lo siento, no encontré información precisa para tu consulta. Algunas sugerencias:\n"
            "- Intenta ser más específico\n"
            "- Usa palabras clave\n"
            "- Verifica la formulación de tu pregunta"
        )

    def manejar_memoria_conversacional(self, pregunta_limpia: str) -> bool:
        if self.contexto_conversacion['sugerencias_previas'] or self.contexto_conversacion['ultimo_articulo']:
            if re.search(r'\b(primero|segundo|tercero|cuarto|quinto|sexto|séptimo|octavo|noveno|décimo)\b',
                         pregunta_limpia):
                return True
            if re.search(r'\b(?:dime )?(?:del )?rac[- ]?0?(\d+)(?!\d)', pregunta_limpia):
                return True
            palabras_confirmacion = ['sí', 'si', 'okay', 'ok', 'de acuerdo']
            if any(p in pregunta_limpia for p in palabras_confirmacion):
                return True
        return False

    def responder_desde_memoria(self, pregunta_limpia: str) -> str:
        # Si el query contiene un nuevo valor de RAC, actualizamos el contexto.
        rac_new = re.search(r'\b(?:dime )?(?:del )?rac[- ]?0?(\d+)(?!\d)', pregunta_limpia)
        if rac_new:
            self.contexto_conversacion['ultimo_rac'] = rac_new.group(1)
        sugerencias = self.contexto_conversacion.get('sugerencias_previas', [])
        if sugerencias:
            selected_index = None
            for i in range(1, len(sugerencias) + 1):
                if ordinal_es(i) in pregunta_limpia:
                    selected_index = i - 1
                    break
            if selected_index is not None:
                if selected_index < len(sugerencias):
                    selected = sugerencias[selected_index]['respuesta']
                    self.contexto_conversacion['sugerencias_previas'] = []
                    return selected
                else:
                    return f"❌ No existe la opción {ordinal_es(selected_index + 1)}."
            rac_match = re.search(r'\b(?:dime )?(?:del )?rac[- ]?0?(\d+)(?!\d)', pregunta_limpia)
            if rac_match:
                rac_filter = rac_match.group(1)
                filtered = [s for s in sugerencias if f"RAC-{rac_filter}" in s['display']]
                if len(filtered) == 1:
                    self.contexto_conversacion['sugerencias_previas'] = []
                    return filtered[0]['respuesta']
                elif len(filtered) > 1:
                    response = f"Varias opciones encontradas para RAC-{rac_filter}:\n"
                    for i, s in enumerate(filtered, 1):
                        response += f"{i}. {s['display']}\n"
                    return response
                else:
                    return f"❌ No se encontraron sugerencias para RAC-{rac_filter}."
            response = "Opciones disponibles:\n"
            for i, s in enumerate(sugerencias, 1):
                response += f"{i}. {s['display']}\n"
            return response
        else:
            ultimo_articulo = self.contexto_conversacion.get('ultimo_articulo')
            ultimo_rac = self.contexto_conversacion.get('ultimo_rac')
            articulos_encontrados = []
            for entrada in self.dataset_completo:
                texto_entrada = (entrada.get('contexto', '') + " " + entrada.get('respuesta', '')).lower()
                if re.search(rf'\barticulo\s*0?{ultimo_articulo}(?!\d)', texto_entrada) and re.search(
                        rf'\brac[- :]?0?{ultimo_rac}(?!\d)', texto_entrada):
                    articulos_encontrados.append(entrada['respuesta'])
            self.contexto_conversacion.update({
                'ultima_consulta': None,
                'ultimo_articulo': None,
                'ultimo_rac': None,
                'sugerencias_previas': []
            })
            return "\n".join(articulos_encontrados) if articulos_encontrados else (
                    f"🤔 No pude encontrar el Artículo {ultimo_articulo}" +
                    (f" en RAC-{ultimo_rac}" if ultimo_rac else "")
            )

    def buscar_coincidencias(self, consulta: str) -> List[Dict]:
        coincidencias = []
        consulta_limpia = quitar_acentos(consulta.lower().strip())
        consulta_normalizada = re.sub(r'[^\w\s]', '', consulta_limpia)
        palabras_clave = {
            'articulo': ['articulo', 'art', 'art.'],
            'proposito': ['proposito', 'objetivo', 'fin', 'finalidad'],
            'rac': ['rac', 'reglamento', 'normativa']
        }
        rac_extraido = None
        for palabra in consulta_normalizada.split():
            rac_match = re.match(r'rac[- :]?0?(\d+)(?!\d)', palabra)
            if rac_match:
                rac_extraido = rac_match.group(1)
                break

        for entrada in self.dataset_completo:
            texto_entrada = quitar_acentos((entrada.get('contexto', '') + " " + entrada.get('respuesta', '')).lower())
            pregunta_entrada = quitar_acentos(entrada.get('pregunta', '').lower())
            entry_r_matches = re.findall(r'\brac[- :]?0?(\d+)(?!\d)', texto_entrada)
            contexto_rac_score = 1 if rac_extraido and rac_extraido in entry_r_matches else 0
            puntajes = {
                'texto_exacto': difflib.SequenceMatcher(None, consulta_limpia, pregunta_entrada).ratio(),
                'palabras_clave': sum(1 for palabra in palabras_clave['articulo'] if palabra in consulta_limpia),
                'contexto_rac': contexto_rac_score,
                'similitud_semantica': difflib.SequenceMatcher(None, consulta_normalizada, pregunta_entrada).ratio()
            }
            relevancia = (
                    puntajes['texto_exacto'] * 0.4 +
                    puntajes['palabras_clave'] * 0.2 +
                    puntajes['contexto_rac'] * 0.3 +
                    puntajes['similitud_semantica'] * 0.1
            )
            if relevancia > 0.3:
                coincidencias.append({
                    'similitud': relevancia,
                    'datos': entrada,
                    'puntajes': puntajes
                })
        return sorted(coincidencias, key=lambda x: (x['puntajes']['contexto_rac'], x['similitud']), reverse=True)[:5]

    def fine_tuning_incremental(self, nuevos_datos: List[Dict], epocas: int = 2):
        print("🌱 Iniciando fine-tuning incremental...")
        dataset_combinado = self.dataset_completo + nuevos_datos

        def preparar_entradas(ejemplos):
            entradas = [f"Pregunta: {item['pregunta']}\nContexto: {item.get('contexto', '')}" for item in ejemplos]
            salidas = [item['respuesta'] for item in ejemplos]
            return entradas, salidas

        entradas, salidas = preparar_entradas(dataset_combinado)
        inputs = self.tokenizer(entradas, padding=True, truncation=True, max_length=256, return_tensors="pt")
        outputs = self.tokenizer(salidas, padding=True, truncation=True, max_length=256, return_tensors="pt")
        dataset = Dataset.from_dict({
            'input_ids': inputs['input_ids'],
            'attention_mask': inputs['attention_mask'],
            'labels': outputs['input_ids']
        }).train_test_split(test_size=0.2)
        argumentos_entrenamiento = TrainingArguments(
            output_dir=self.dir_modelo_fine_tuned,
            num_train_epochs=epocas,
            per_device_train_batch_size=4,
            learning_rate=1e-4,
            logging_dir=os.path.join(self.directorio_checkpoints, 'logs'),
            save_strategy="epoch",
            evaluation_strategy="epoch",
            load_best_model_at_end=True
        )
        data_collator = DataCollatorForSeq2Seq(tokenizer=self.tokenizer, model=self.modelo, padding=True)
        trainer = Trainer(
            model=self.modelo,
            args=argumentos_entrenamiento,
            train_dataset=dataset['train'],
            eval_dataset=dataset['test'],
            data_collator=data_collator
        )
        trainer.train()
        trainer.save_model(self.dir_modelo_fine_tuned)
        self.dataset_completo = dataset_combinado
        with open(self.ruta_dataset, 'w', encoding='utf-8') as f:
            json.dump(self.dataset_completo, f, indent=2)
        print("✅ Fine-tuning incremental completado")

    def _inicializar_modelo(self):
        print(f"🚀 Inicializando modelo base: {self.modelo_base}")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.modelo_base)
            self.tokenizer.save_pretrained(self.dir_modelo_base)
            modelo_base = AutoModelForSeq2SeqLM.from_pretrained(self.modelo_base)
            if PEFT_DISPONIBLE:
                print("🔧 Configurando adaptación LoRA...")
                config_lora = LoraConfig(
                    r=16,
                    lora_alpha=32,
                    target_modules=["q", "v"],
                    lora_dropout=0.1,
                    bias="none",
                    task_type="SEQ_2_SEQ_LM"
                )
                self.modelo = get_peft_model(modelo_base, config_lora)
            else:
                self.modelo = modelo_base
            print("✅ Modelo inicializado correctamente")
        except Exception as e:
            print(f"❌ Error durante la inicialización: {e}")
            raise


def main():
    print("🌟 Modelo EMI - Interfaz Interactiva con Memoria Contextual")
    modelo = ModeloConsultaEMI()
    print("✨ Modelo listo. Escribe 'salir' para terminar.")

    while True:
        pregunta = input("\n📝 Tu pregunta: ")
        if pregunta.lower() == 'salir':
            print("👋 ¡Hasta luego!")
            break
        try:
            respuesta = modelo.generar_respuesta(pregunta)
            print(f"\n🤖 Respuesta: {respuesta}")

            # Verificar si la respuesta indica que no se encontró información
            if "no encontré información precisa" in respuesta:
                actualizar = input("\n¿Deseas actualizar con nuevos datos? (si/no): ").lower().strip()
                if actualizar in ['si', 'sí']:
                    nueva_pregunta = input("Ingresa la pregunta: ")
                    nuevo_contexto = input("Ingresa el contexto: ")
                    nueva_respuesta = input("Ingresa la respuesta: ")

                    # Crear un nuevo dataset con la entrada proporcionada
                    nuevos_datos = [{
                        "pregunta": nueva_pregunta,
                        "contexto": nuevo_contexto,
                        "respuesta": nueva_respuesta
                    }]

                    print("\n🌱 Iniciando fine-tuning incremental con los nuevos datos...")
                    modelo.fine_tuning_incremental(nuevos_datos, epocas=2)
                    print("✅ Actualización completada. El modelo ahora cuenta con la nueva información.")

        except Exception as e:
            print(f"❌ Ocurrió un error: {e}")


if __name__ == "__main__":
    main()
