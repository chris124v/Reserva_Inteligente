#Archivo de definicion de la conexion de la api con redis, esto para cache

# redis = Libreria de Python que permite interactuar con el servidor Redis
import redis

# settings = Variables de configuracion host, puerto, ttl y demas
from app.config import settings


# redis_client = Instancia global del cliente Redis
# decode_responses=True hace que Redis devuelva strings en vez de bytes
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=int(settings.REDIS_PORT),
    decode_responses=True
)

#Funcion para obtener el cliente de redis
def get_redis():

    return redis_client