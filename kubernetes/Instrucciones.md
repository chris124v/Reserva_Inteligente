# Scripts - Reserva Inteligente Kubernetes

En este markdown de instrucciones incluimos muchos de los comandos para ver datos del sistema y hacer el deployment.

Lo primero para hacer por ahora descargar la imagen de docker despues se puede hacer todo lo demas, esto es con el dockerfile.

```powershell
docker build -t reservainteligente-api:v7 .
kubectl apply -f kubernetes/api/main-api/deployment.yaml
kubectl apply -f kubernetes/api/search-service/deployment.yaml
```
Nota: cambiar entre bds asi

```
kubectl apply -f kubernetes/config/configmap.yaml
kubectl get configmap app-config -n reservainteligente -o jsonpath='{.data.DATABASE_TYPE}' ; Write-Host ""
```

## 1. Desplegar (deploy-all.ps1)

```powershell
.\deploy-all.ps1
```
Despliega todo: namespace, configuracion, bases de datos y API.

## 2. Limpiar (cleanup-all.ps1)

```powershell

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
powershell -ExecutionPolicy Bypass -File .\cleanup-all.ps1

.\cleanup-all.ps1
```
Elimina todos los recursos. Pide confirmacion antes por si las dudas. Ese primer execution policy es por si no funciona con un solo comando.

## 3. Estado (status.ps1)

```powershell
.\status.ps1
```
Verifica el estado del ambiente completo.

## 4. Ver datos del Sistema

Aqui vemos pods, services y pvcs

``` powershell
kubectl get pods -n reservainteligente
kubectl get svc -n reservainteligente
kubectl get pvc -n reservainteligente
kubectl get all -n reservainteligente
```

## 5. Ver logs para debug

Tanto para todos como para un pod especifico

``` powershell
kubectl logs -l app=main-api -n reservainteligente
kubectl logs <nombre-pod> -n reservainteligente
kubectl describe pod <nombre-pod> -n reservainteligente
kubectl describe deployment main-api -n reservainteligente
```
## 6. API

Algunos comando importantes para el despliegue de la api

``` powershell
kubectl rollout restart deployment/main-api -n reservainteligente #Reiniciar la api
kubectl port-forward svc/api-service 8000:80 -n reservainteligente #Forward local de la api
kubectl logs -f -l app=main-api -n reservainteligente #Ver logs
```
## 7. Mongo

Como entramos a mongo y comandos basicos

```powershell
# Opción 1: Por Mongos 
kubectl exec -it mongos-76f489dbbc-w5f67 -n reservainteligente -- mongosh

# Opción 2: Directamente a una replica del shard
kubectl exec -it mongors1-0 -n reservainteligente -- mongosh

# Dentro de mongosh:
use reserva_inteligente
show collections
db.restaurants.find().pretty()
db.restaurants.countDocuments()
rs.status()  # Ver estado del replica set
```
## 8. Postgres

Como entramos a postgres y comandos basicos

```

$pod = kubectl get pods -n reservainteligente -l app=main-api -o jsonpath='{.items[0].metadata.name}'
kubectl exec -n reservainteligente $pod -c main-api -- python -m app.database.init_db #Iniciar bd si da error

$pod = kubectl get pods -n reservainteligente -l app=main-api -o jsonpath='{.items[0].metadata.name}'; 
kubectl exec -n reservainteligente $pod -- printenv DATABASE_TYPE #Esto para verificar que si esta en postgres


kubectl exec -it postgres-0 -n reservainteligente -- psql -U postgres -d restaurantes_db

\dt
SELECT * FROM restaurants;
```

## 9. Aplicar cambios a configs

Luego se puede aplicar a archivos directos pero esto es la base

```
#Aplicar cambios
kubectl apply -f kubernetes/
kubectl apply -f kubernetes/api/
kubectl apply -f kubernetes/databases/

#Borrar recursos
kubectl delete -f kubernetes/
kubectl delete pod <nombre> -n reservainteligente
```

## 10. Redis

Aqui voy a dejar algunos comandos importantes para interactuar con redis y el resto

Aplicar cambios al cluster

```powershell
kubectl apply -f kubernetes/databases/redis/ #Tanto a service como deployment

kubectl get pods -n reservainteligente
kubectl get svc -n reservainteligente

```

Comandos para entrar a la bd de redis y ver las keys

```powershell
kubectl exec -it deployment/redis -n reservainteligente -- redis-cli

keys *
ttl restaurants:all:0:10
get restaurants:all:0:10

```

Comandos para probar endpoints en terminal y ver si hace mis o hit

```
curl -UseBasicParsing http://localhost:8000/restaurants/
curl -UseBasicParsing http://localhost:8000/restaurants/
```

Logs, aqui vemos si hizo hit o miss con el endpoint

```
kubectl logs deployment/main-api -n reservainteligente --tail=100
```

## 10. Elastic Search Comandos

Aplicar cambios a los archivos de config

```
kubectl apply -f kubernetes/databases/elasticsearch/pvc.yaml
kubectl apply -f kubernetes/databases/elasticsearch/service.yaml
kubectl apply -f kubernetes/databases/elasticsearch/statefulset.yaml
```

Revisar pods, service y logs

```
kubectl get pods -n reservainteligente
kubectl get svc -n reservainteligente
kubectl logs elasticsearch-0 -n reservainteligente
```

Hacer forward del puerto y probarlo

```
kubectl port-forward service/elasticsearch 9200:9200 -n reservainteligente
kubectl port-forward svc/search-service 8001:80 -n reservainteligente
curl http://localhost:9200
```

## 11. Search Service (Microservicio)

Construir imagen local del microservicio de busqueda

```powershell
docker build -t reservainteligente-search:v2 -f search_service/Dockerfile .
```

Aplicar deployment y service del search-service

```powershell
kubectl apply -f kubernetes/api/search-service/
kubectl set image deployment/search-service search-service=reservainteligente-search:v2 -n reservainteligente
kubectl rollout restart deployment/search-service -n reservainteligente
kubectl rollout status deployment/search-service -n reservainteligente
kubectl get pods -n reservainteligente -l app=search-service
kubectl get svc -n reservainteligente
```

Ver logs si hay errores (CrashLoopBackOff / ImagePull)

```powershell
kubectl logs -n reservainteligente deployment/search-service --tail=200
kubectl describe pod -n reservainteligente -l app=search-service
```

Probar en Swagger del search-service

```powershell
kubectl port-forward svc/search-service 8001:80 -n reservainteligente
```

## 12. Nginx Load Balancer

Comandos para aplicar el balanceador de Nginx

```powershell
kubectl apply -f kubernetes/balancer/nginx-configmap.yaml
kubectl apply -f kubernetes/balancer/nginx-deployment.yaml
kubectl apply -f kubernetes/balancer/nginx-service.yaml
kubectl get pods -n reservainteligente -l app=nginx-balancer
kubectl get svc -n reservainteligente | Select-String "nginx"
```

Hacer port-forward para probarlo localmente

```powershell
kubectl port-forward svc/nginx-service 8080:80 -n reservainteligente

kubectl logs -f -n reservainteligente deployment/nginx-balancer --tail=200
```

Para probar Nginx solo necesitas el port-forward del `nginx-service`; no hace falta abrir `api-service` ni `search-service` para estas pruebas.

Probar rutas por Nginx

```powershell
curl -UseBasicParsing http://localhost:8080/api/health
curl -UseBasicParsing http://localhost:8080/api/restaurants/
curl -UseBasicParsing http://localhost:8080/search/menus?q=pollo
curl -UseBasicParsing http://localhost:8080/search/menus/category/pizza
```

Luego abres:

```text
http://localhost:8001/docs
```

## 13. Escalabilidad con KS

Para probar desde NGINX, faltaria con search porque no esta mapeado en config map 

```
kubectl port-forward svc/nginx-service 8080:80 -n reservainteligente

curl -UseBasicParsing http://localhost:8080/api/instance
curl -UseBasicParsing http://localhost:8080/api/instance
curl -UseBasicParsing http://localhost:8080/api/instance
curl -UseBasicParsing http://localhost:8080/api/instance
curl -UseBasicParsing http://localhost:8080/api/instance

```

Probar desde el service de api

```
kubectl port-forward svc/api-service 8000:80 -n reservainteligente

curl -UseBasicParsing http://localhost:8000/instance
curl -UseBasicParsing http://localhost:8000/instance
curl -UseBasicParsing http://localhost:8000/instance
```

Probar desde el servicio de busqueda

```
kubectl port-forward svc/search-service 8001:80 -n reservainteligente

kubectl logs search-service-667747b5b7-9p5mm -n reservainteligente --tail=20
kubectl logs search-service-667747b5b7-dd8n4 -n reservainteligente --tail=20
kubectl logs search-service-667747b5b7-tp2vf -n reservainteligente --tail=20

curl -UseBasicParsing http://localhost:8001/instance
curl -UseBasicParsing http://localhost:8001/instance
curl -UseBasicParsing http://localhost:8001/instance
curl -UseBasicParsing http://localhost:8001/instance
```

Validar pods escalados, deberia haber 3 replica por cada servicio de api

```
kubectl get pods -n reservainteligente
```
## 14. OLAP Logs y inicializacion

Estado general

```
kubectl get pods -n reservainteligente -l "app in (hdfs-namenode,hdfs-datanode,hive-metastore-db,hive-metastore,hiveserver2)"
```

Logs HDFS NameNode

```
kubectl logs -n reservainteligente hdfs-namenode-0 --tail=20
```

Logs HDFS DataNode

```
kubectl logs -n reservainteligente hdfs-datanode-0 --tail=20
```

Logs Hive Metastore

```
kubectl logs -n reservainteligente -l app=hive-metastore --tail=20
```

Logs HiveServer2

```
kubectl logs -n reservainteligente -l app=hiveserver2 --tail=20
```

Web UI HDFS (ver cluster y archivos)
```
kubectl port-forward -n reservainteligente svc/hdfs-namenode 9870:9870
```

Web UI HiveServer2 (ver queries activas)
```
kubectl port-forward -n reservainteligente svc/hiveserver2 10002:10002
```
