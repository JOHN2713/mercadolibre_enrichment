from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Cargar variables del .env
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")

if not MONGODB_URI:
    raise ValueError("No se encontró MONGODB_URI en el .env")

# Conectar al cluster
client = MongoClient(MONGODB_URI)

# Elegir BD y colección
db = client["ml_reviews"]
collection = db["raw_reviews"]

# Insertar un documento de prueba
doc = {"tipo": "test_conexion", "mensaje": "Hola MongoDB desde Python"}
result = collection.insert_one(doc)

print("Documento insertado con _id:", result.inserted_id)
