import subprocess
import sys


# Scripts a ejecutar en orden
def run_script(path):
    print(f"\n⬆️ Ejecutando: {path}\n")
    result = subprocess.run([sys.executable, path])

    if result.returncode != 0:
        print(f"❌ Error ejecutando {path}")
        exit(1)
    else:
        print(f"✅ Finalizado: {path}\n")


scripts_ordenados = [
    "./scripts/cargar_documentos.py",
    "./scripts/guardar_mongodb.py",
    "./scripts/vectorizar_texto.py",
    "./scripts/preparar_datos.py",
    "./scripts/preguntas_respuestas.py",
    "./scripts/enriquecer_dataset.py"
]

if __name__ == "__main__":
    print("\n🌟 Pipeline de Preparación - Asistente EMI\n")
    for script in scripts_ordenados:
        run_script(script)

    print("\n🤖 Todo listo. Puedes ejecutar ahora: python modelo_consulta.py")
