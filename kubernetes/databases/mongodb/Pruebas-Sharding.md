# Prueba Sharding en Terminal

Aqui dejo algunos de los comandos para probar sharding sin necesidad de pruebas unitarias, osea prueba en terminal.

## Verificacion

Aqui verificamos que si este en mongos y no en una bd simple, solo cambiar nombre de pods porque cambian obvio

```powershell
kubectl exec -it main-api-6ffdc95f4-fgffl -n reservainteligente -- printenv MONGODB_URI

kubectl exec -it main-api-6ffdc95f4-th2dt  -n reservainteligente -- printenv MONGODB_URI
```

## Conectarse al shard

Comandos para conectarse al shard

```powershell

kubectl exec -it mongors1-0 -n reservainteligente -- mongosh #Entrar a mongsh
rs.status() #Verificar status muy importante

```

esto indica que hay 
mongors1-0 = PRIMARY
mongors1-1 = SECONDARY
mongors1-2 = SECONDARY

## Servicio Mongos

Aqui indicamos como entrar al servicio de mongos y ver el replica set

``` powershell
kubectl exec -it mongos-76f489dbbc-rmhqt -n reservainteligente -- mongosh #Entrar 

use reserva_inteligente
db.menus.getShardDistribution()
db.reservations.getShardDistribution()

#Verificacion optima de shards
```