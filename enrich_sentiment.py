from pymongo import MongoClient
from dotenv import load_dotenv
from transformers import pipeline
import os
import time

# ------------------------
# Configuración MongoDB
# ------------------------
load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")

if not MONGODB_URI:
    raise ValueError("No se encontró MONGODB_URI en el .env")

client = MongoClient(MONGODB_URI)
db = client["ml_reviews"]
reviews_col = db["raw_reviews"]

# ------------------------
# Cargar modelo de sentimiento (multilingüe español)
# ------------------------
print("="*80)
print("CARGANDO MODELO DE ANÁLISIS DE SENTIMIENTO")
print("="*80)
print("Modelo: pysentimiento/robertuito-sentiment-analysis")
print("Esto puede tardar un poco la primera vez...")

MODEL_NAME = "pysentimiento/robertuito-sentiment-analysis"

try:
    sentiment_pipeline = pipeline(
        "sentiment-analysis",
        model=MODEL_NAME,
        tokenizer=MODEL_NAME,
        device=-1  # -1 = CPU, 0 = GPU
    )
    print("Modelo cargado correctamente\n")
except Exception as e:
    print(f"Error al cargar modelo: {e}")
    exit(1)

def analizar_sentimiento(texto: str):
    """
    Usa modelo en español (pysentimiento/robertuito) que devuelve:
    POS / NEG / NEU
    
    Mapeo:
      - POS → stars=5, score=1.0, label="positivo"
      - NEG → stars=1, score=-1.0, label="negativo"
      - NEU → stars=3, score=0.0, label="neutral"
    """
    if not texto or not texto.strip():
        return None, None, None

    texto_limpio = texto.strip()
    
    try:
        # Limitar a 512 tokens (límite del modelo)
        result = sentiment_pipeline(texto_limpio[:512])[0]
        raw_label = result["label"]  # "POS", "NEG", "NEU"
        confidence = result.get("score", 0.0)

        if raw_label == "POS":
            sentiment_label = "positivo"
            sentiment_score = 1.0
            stars = 5
        elif raw_label == "NEG":
            sentiment_label = "negativo"
            sentiment_score = -1.0
            stars = 1
        else:  # NEU
            sentiment_label = "neutral"
            sentiment_score = 0.0
            stars = 3

        return stars, sentiment_score, sentiment_label, confidence
    
    except Exception as e:
        print(f" Error al analizar: {str(e)[:50]}...")
        return None, None, None, None


def enriquecer_lote(limit=50, mostrar_ejemplos=False):
    """
    Toma un lote de reseñas sin sentimiento y las enriquece.
    """
    cursor = reviews_col.find(
        {"sentiment_score": {"$exists": False}},
        limit=limit
    )

    docs = list(cursor)
    if not docs:
        return 0

    exitosos = 0
    fallidos = 0

    for idx, doc in enumerate(docs, 1):
        texto = doc.get("reseña_texto") or doc.get("texto")
        
        if not texto:
            fallidos += 1
            continue

        stars, score, label, confidence = analizar_sentimiento(texto)

        if stars is None:
            fallidos += 1
            continue

        update_fields = {
            "sentiment_stars": stars,
            "sentiment_score": score,
            "sentiment_label": label,
            "sentiment_confidence": confidence,
            "sentiment_model": MODEL_NAME,
        }

        reviews_col.update_one(
            {"_id": doc["_id"]},
            {"$set": update_fields}
        )

        exitosos += 1

        # Mostrar ejemplos solo si está activado
        if mostrar_ejemplos and idx <= 3:
            print(f"  ✓ [{idx}] {label.upper()}: {texto[:60]}...")

    return exitosos, fallidos


def main():
    print("="*80)
    print("ENRIQUECIMIENTO DE SENTIMIENTOS")
    print("="*80)
    
    # Estadísticas iniciales
    total_reviews = reviews_col.count_documents({})
    con_sentimiento = reviews_col.count_documents({"sentiment_score": {"$exists": True}})
    sin_sentimiento = total_reviews - con_sentimiento
    
    print(f"\n📊 Estado actual:")
    print(f"  • Total de reseñas: {total_reviews}")
    print(f"  • Con sentimiento analizado: {con_sentimiento}")
    print(f"  • Pendientes de analizar: {sin_sentimiento}")
    
    if sin_sentimiento == 0:
        print("\nNo hay reseñas pendientes de analizar")
        return
    
    # Distribución de sentimientos existentes
    if con_sentimiento > 0:
        print(f"\nDistribución actual de sentimientos:")
        for label in ["positivo", "neutral", "negativo"]:
            count = reviews_col.count_documents({"sentiment_label": label})
            porcentaje = (count / con_sentimiento) * 100 if con_sentimiento > 0 else 0
            print(f"  • {label.capitalize()}: {count} ({porcentaje:.1f}%)")
    
    # Opciones
    print(f"\nOPCIONES:")
    print(f"  1. Procesar TODAS las reseñas pendientes ({sin_sentimiento} reseñas)")
    print(f"  2. Procesar en lotes de 50 (modo interactivo)")
    print(f"  3. Reanalizar TODO (borrar sentimientos existentes)")
    
    opcion = input("\nSelecciona una opción (1/2/3): ").strip()
    
    if opcion == "3":
        confirmar = input("¿Seguro que quieres BORRAR todos los sentimientos? (si/no): ").strip().lower()
        if confirmar == "si":
            result = reviews_col.update_many(
                {},
                {"$unset": {
                    "sentiment_stars": "",
                    "sentiment_score": "",
                    "sentiment_label": "",
                    "sentiment_confidence": "",
                    "sentiment_model": ""
                }}
            )
            print(f"Eliminados sentimientos de {result.modified_count} reseñas")
            sin_sentimiento = total_reviews
        else:
            print("Operación cancelada")
            return
    
    # Procesar reseñas
    total_procesadas = 0
    total_exitosas = 0
    total_fallidas = 0
    lote_num = 0
    
    print(f"\n{'='*80}")
    print(f"PROCESANDO RESEÑAS")
    print(f"{'='*80}\n")
    
    try:
        while True:
            lote_num += 1
            print(f"Lote {lote_num}:")
            
            exitosas, fallidas = enriquecer_lote(
                limit=50, 
                mostrar_ejemplos=(lote_num == 1)  # Solo mostrar ejemplos en el primer lote
            )
            
            if exitosas == 0 and fallidas == 0:
                print("No hay más reseñas pendientes")
                break
            
            total_procesadas += (exitosas + fallidas)
            total_exitosas += exitosas
            total_fallidas += fallidas
            
            print(f"  ✓ Exitosas: {exitosas} | Fallidas: {fallidas}")
            print(f"  Progreso: {total_exitosas}/{sin_sentimiento}")
            
            # Si es modo interactivo (opción 2), preguntar si continuar
            if opcion == "2":
                continuar = input("\n  ¿Continuar con el siguiente lote? (s/n): ").strip().lower()
                if continuar != "s":
                    print("\nProceso pausado por el usuario")
                    break
            
            print()  # Línea en blanco entre lotes
            
    except KeyboardInterrupt:
        print("\n\nProceso interrumpido por el usuario (Ctrl+C)")
    
    # Resumen final
    print(f"\n{'='*80}")
    print(f"PROCESO COMPLETADO")
    print(f"{'='*80}")
    print(f"Reseñas analizadas exitosamente: {total_exitosas}")
    print(f"Reseñas con error: {total_fallidas}")
    print(f"Total procesadas: {total_procesadas}")
    
    # Estadísticas finales
    con_sentimiento_final = reviews_col.count_documents({"sentiment_score": {"$exists": True}})
    sin_sentimiento_final = total_reviews - con_sentimiento_final
    
    print(f"\nEstado final:")
    print(f"  • Con sentimiento: {con_sentimiento_final}/{total_reviews}")
    print(f"  • Pendientes: {sin_sentimiento_final}")
    
    # Distribución final
    print(f"\nDistribución de sentimientos:")
    for label in ["positivo", "neutral", "negativo"]:
        count = reviews_col.count_documents({"sentiment_label": label})
        porcentaje = (count / con_sentimiento_final) * 100 if con_sentimiento_final > 0 else 0
        emoji = "😊" if label == "positivo" else "😐" if label == "neutral" else "😞"
        print(f"  {emoji} {label.capitalize()}: {count} ({porcentaje:.1f}%)")
    
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
