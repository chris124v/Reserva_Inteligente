# Prueba Sharding en Terminal

Aqui dejo algunos de los comandos para probar sharding sin necesidad de pruebas unitarias, osea prueba en terminal.

## Verificacion

Aqui verificamos que si este en mongos y no en una bd simple, solo cambiar nombre de pods porque cambian obvio

```powershell
kubectl exec -it main-api-57b6d85444-wsz5z -n reservainteligente -- printenv MONGODB_URI

kubectl exec -it main-api-6ffdc95f4-th2dt  -n reservainteligente -- printenv MONGODB_URI
```

## Conectarse al shard

Comandos para conectarse al shard

```powershell

kubectl exec -it mongors1-0 -n reservainteligente -- mongosh #Entrar a mongsh


# 1. Ver estado del Replica Set
rs.status()
# Verás: PRIMARY (mongors1-0), SECONDARY (mongors1-1), SECONDARY (mongors1-2)

```

## Servicio Mongos

Aqui indicamos como entrar al servicio de mongos y ver el replica set

``` powershell
kubectl exec -it mongos-76f489dbbc-w5f67 -n reservainteligente -- mongosh #Entrar 

use reserva_inteligente

// Ver todos los restaurantes
db.restaurants.find().pretty()

# 2. Ver la configuración de Sharding
sh.status()
# Te mostrará los shards, bases de datos y colecciones shardeadas

# 3. Ver distribución en cada colección
db.restaurants.getShardDistribution()
db.menus.getShardDistribution()
db.orders.getShardDistribution()
db.reservations.getShardDistribution()
# Mostrarán todos en el mismo shard (mongors1)

# Contar documentos
db.restaurants.countDocuments()
db.menus.countDocuments()
db.orders.countDocuments()
db.reservations.countDocuments()

# Ver el oplog (historial de replicación)
use local
db.oplog.rs.find().sort({$natural: -1}).limit(5).pretty()
kubectl port-forward svc/mongos-service 27017:27017 -n reservainteligente #Conectarse al shard por medio de compass

#Verificacion optima de shards
```

## Shard Idempotente en caso de limpiar bd para testing

```
kubectl delete job mongo-init-idempotent -n reservainteligente --wait
kubectl apply -f kubernetes/databases/mongodb/sharding/init-sharding-job-idempotent.yaml
kubectl get jobs -n reservainteligente
kubectl logs -n reservainteligente job/mongo-init-idempotent
```

## Replicas

Para verificar que esta distribuido en replicas

``` powershell
# Terminal 1: Conectar a primary (mongors1-0)
kubectl exec -it mongors1-0 -n reservainteligente -- mongosh
use reserva_inteligente
db.restaurants.countDocuments()

# Terminal 2: Conectar a secondary (mongors1-1)
kubectl exec -it mongors1-1 -n reservainteligente -- mongosh
use reserva_inteligente
db.restaurants.countDocuments()  # Debe ser igual

# Terminal 3: Conectar a secondary (mongors1-2)
kubectl exec -it mongors1-2 -n reservainteligente -- mongosh
use reserva_inteligente
db.restaurants.countDocuments()  # Debe ser igual
```