from elasticsearch import Elasticsearch
from app.config import settings

# Configuración del cliente de Elasticsearch
es_client = Elasticsearch(settings.ELASTICSEARCH_URL)