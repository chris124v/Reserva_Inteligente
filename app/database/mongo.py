import os
from pymongo import MongoClient
from pymongo.database import Database

_client: MongoClient | None = None

# Retorna el cliente MongoDB, creandolo si no existe.
def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        _client = MongoClient(mongo_uri)
    return _client

# Retorna la base de datos MongoDB configurada en .env.
def get_mongo_db() -> Database:
    client = get_mongo_client()
    db_name = os.getenv("MONGODB_DB_NAME", "reserva_inteligente")
    return client[db_name]