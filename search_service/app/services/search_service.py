import os
from elasticsearch import Elasticsearch

ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
es_client = Elasticsearch(ELASTICSEARCH_URL)

# Archivo donde definimos las funciones para interactuar con elastic search
#Incluimos indexar menu, buscar menus por texto y categoria
#tambien reindexamos

MENUS_INDEX = "menus"

def _field(menu, key, default=None):
    if isinstance(menu, dict):
        return menu.get(key, default)
    return getattr(menu, key, default)

#Funcion para crear el indice en elastic donde se guardan los menus
def create_menus_index():

    #Si el indice ya existe no pasa nada
    if es_client.indices.exists(index=MENUS_INDEX):
        return

    #Sino entonces hacemos el mapeo clomplego de cada documento, el id se guarda como keyword al igual que categoria
    mapping = {
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "nombre": {"type": "text"},
                "categoria": {"type": "keyword"},
                "descripcion": {"type": "text"},
                "precio": {"type": "float"},
                "disponible": {"type": "boolean"},
                "tiempo_preparacion": {"type": "integer"},
                "restaurante_id": {"type": "keyword"}
            }
        }
    }

    #Crea el indice usando el mapping 
    es_client.indices.create(index=MENUS_INDEX, body=mapping)

#Definimos una funcion para guardar el menu en elastic
def index_menu(menu):

    #Obtiene el id del menu
    menu_id = str(_field(menu, "id", None) or _field(menu, "_id", None) or "")

    #Creamos el documento que se va a guardar en elastic 
    document = {
        "id": menu_id,
        "nombre": _field(menu, "nombre", ""),
        "categoria": _field(menu, "categoria", ""),
        "descripcion": _field(menu, "descripcion", None) or "Producto sin descripción",
        "precio": float(_field(menu, "precio", 0)),
        "disponible": _field(menu, "disponible", True),
        "tiempo_preparacion": int(_field(menu, "tiempo_preparacion", 0)),
        "restaurante_id": str(_field(menu, "restaurante_id", ""))
    }

    #Llama a elastic para guardar el documento, lo guarda en el indice de menus
    es_client.index(
        index=MENUS_INDEX,
        id=menu_id,
        document=document
    )

#Buscamos menus por texto, osea descripcion y categoria y nombre
def search_menus(query: str):

    #Definimos el indice
    create_menus_index()

    #Response hace una busqueda en elastic 
    response = es_client.search(
        index=MENUS_INDEX,
        query={
            "multi_match": { #Buscamos el mismo texto en varios campos
                "query": query,
                "fields": ["nombre", "categoria", "descripcion"]
            }
        }
    )

    #Extraemos solo el documento real del resultado, con hits como en redis
    return [hit["_source"] for hit in response["hits"]["hits"]]

#Este seria para buscarlo solo por categoria
def search_menus_by_category(categoria: str):
    create_menus_index()

    #Aqui a diferencia no es multimatch solo term que busca categoria en especifico 
    response = es_client.search(
        index=MENUS_INDEX,
        query={
            "term": {
                "categoria": categoria
            }
        }
    )

    return [hit["_source"] for hit in response["hits"]["hits"]]

#Esto seria para reconstruir todo el indice de elastic
def reindex_menus(menus):

    #Si ya existe lo elimina
    if es_client.indices.exists(index=MENUS_INDEX):
        es_client.indices.delete(index=MENUS_INDEX)

    #Crea otra vez con el mapping que es
    create_menus_index()

    #Contador de indexacion
    total = 0

    #Recorre cada menu y lo indexa, sumando al contador
    for menu in menus:
        index_menu(menu)
        total += 1

    #Deja dispobiles los datos recien indexados
    es_client.indices.refresh(index=MENUS_INDEX)

    #Devuelve un mensaje
    return {
        "message": "Menus reindexed successfully",
        "total_indexed": total
    }
