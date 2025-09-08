# -*- coding: utf-8 -*-
"""
Cliente de prueba para el servidor de simulación (versión con config. interna).

Este script:
1. Llama al endpoint '/run_simulation' del servidor Flask usando una petición GET.
2. Recibe la respuesta del servidor.
3. Imprime un resumen de los resultados en la consola.
4. Guarda la respuesta JSON completa en un archivo 'simulation_results.json'.
"""

import requests
import json

# --- Configuración ---
SERVER_URL = "http://127.0.0.1:5000/run_simulation"
RESULTS_FILE = "simulation_results.json"

def run_test():
    """
    Función principal para ejecutar la prueba del endpoint.
    """
    print("🚀 Iniciando prueba del cliente para el servidor de simulación...")
    print(f"📡 Enviando petición a: {SERVER_URL}")

    try:
        # 1. Enviar la petición GET al servidor
        # No se necesita enviar datos, solo llamar a la URL.
        # Se añade un timeout largo por si la simulación tarda en procesar.
        response = requests.get(SERVER_URL, timeout=300) 

        # 2. Procesar la respuesta del servidor
        if response.status_code == 200:
            print("✅ ¡Respuesta recibida exitosamente del servidor! (Código 200)")
            
            results = response.json()
            
            # Guardar los resultados completos en un archivo
            with open(RESULTS_FILE, 'w') as f:
                json.dump(results, f, indent=4)
            print(f"💾 Resultados completos guardados en '{RESULTS_FILE}'")

            # Imprimir un resumen legible en la consola
            print("\n--- RESUMEN DE LA SIMULACIÓN ---")
            stats = results.get("final_stats", {})
            print(f"  Resultado Final: {stats.get('result', 'N/A')}")
            print(f"  Pasos Totales: {stats.get('total_steps', 'N/A')}")
            print(f"  Rehenes Rescatados: {stats.get('hostages_rescued', 'N/A')}")
            print(f"  Rehenes Perdidos: {stats.get('hostages_lost', 'N/A')}")
            print(f"  Daño Estructural: {stats.get('structural_damage', 'N/A')}")
            print("----------------------------------\n")

        else:
            # Si algo sale mal, mostrar el error que devuelve el servidor
            print(f"❌ Error del servidor (Código {response.status_code}):")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("❌ Error de Conexión: No se pudo conectar al servidor.")
        print("Asegúrate de que el servidor Flask ('app.py') se esté ejecutando.")
    except requests.exceptions.Timeout:
        print("❌ Error: La petición excedió el tiempo de espera (timeout).")
        print("La simulación podría estar tardando demasiado en completarse.")
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado durante la petición: {e}")


if __name__ == "__main__":
    run_test()