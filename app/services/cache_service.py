# Defininimos un servicio de cache usando Redis
# Sirve para guardar respuestas frecuentes y evitar consultas repetidas a la bd que se use

import json
from app.database.redis import get_redis
from app.config import settings


class CacheService:

    #Constructr que inicializa el cliente de redis junto con el TTL
    def __init__(self):
        self.redis = get_redis()
        self.ttl = int(settings.REDIS_TTL)
        self.enabled = settings.REDIS_ENABLED.lower() == "true"

    #Obtiene un valor desde redis unsando una key
    def get(self, key: str):
        
        #Si redis no se activa no pasa nada
        if not self.enabled:
            return None


        try:
            data = self.redis.get(key) #Busca el valor asociado a la key
            if data:
                return json.loads(data) #Si existe devuelve el valor en json y lo convierte a python
            return None
        except Exception:
            return None

    #Guarda un valor en redis usando una key y el TTL definido
    def set(self, key: str, value):
        
        #Sino pasa nada, no pasa nada
        if not self.enabled:
            return

        try:
            self.redis.setex(key, self.ttl, json.dumps(value)) #Guarda la key con el tiempo de expiracion que definimos, pasa de python a json
        except Exception:
            pass
    
    #Elimina una key especifica de redis
    def delete(self, key: str):
        
        #Nada
        if not self.enabled:
            return

        #La elimina
        try:
            self.redis.delete(key)
        except Exception:
            pass
    
    #Elimina multiples keys usando un patron, por ejemplo menus:* elimina todas las keys que empiezan con menus
    def delete_pattern(self, pattern: str):
       
        if not self.enabled:
            return

        #Busca todas las keys que coincidan con el patron y las elimina
        try:
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
        except Exception:
            pass


# instancia global para usar en toda la app
cache_service = CacheService()