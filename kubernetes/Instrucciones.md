# Scripts - Reserva Inteligente Kubernetes

En este markdown de instrucciones incluimos muchos de los comandos para ver datos del sistema y hacer el deployment.

Lo primero para hacer por ahora descargar la imagen de docker despues se puede hacer todo lo demas, esto es con el dockerfile.

```powershell
docker build -t reservainteligente-api:v3 .
kubectl apply -f kubernetes/api/main-api/deployment.yaml

```
Nota: cambiar entre bds asi

```
kubectl apply -f kubernetes/config/configmap.yaml
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

```
kubectl exec -it mongo-0 -n reservainteligente -- mongosh

use reserva_inteligente
show collections
db.test.find()

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

Abrir en navegador:

```text
http://localhost:8001/docs
```

Orden recomendado para probar en Swagger:

```text
1) POST /search/reindex
2) GET /search/menus?q=pollo
3) GET /search/menus/category/{categoria}
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
```

Para probar Nginx solo necesitas el port-forward del `nginx-service`; no hace falta abrir `api-service` ni `search-service` para estas pruebas.

Probar rutas por Nginx

```powershell
curl -UseBasicParsing http://localhost:8080/api/health
curl -UseBasicParsing http://localhost:8080/api/restaurants/
curl -UseBasicParsing http://localhost:8080/search/menus?q=pollo
curl -UseBasicParsing http://localhost:8080/search/menus/category/pizza
```

Si lo que quieres es probar Swagger del microservicio de búsqueda, entonces sí debes hacer port-forward directo a `search-service`:

```powershell
kubectl port-forward svc/search-service 8001:80 -n reservainteligente
```

Luego abres:

```text
http://localhost:8001/docs
```

Orden recomendado para Swagger:

```text
1) POST /search/reindex
2) GET /search/menus?q=pollo
3) GET /search/menus/category/{categoria}
```

En resumen:

```text
- Para probar Nginx: solo port-forward del nginx-service.
- Para probar Swagger: solo port-forward del search-service.
- No necesitas abrir api-service y search-service al mismo tiempo para validar Nginx.
```

Si quieres probar Swagger de la API principal, entonces sí usa el port-forward de `api-service`:

```powershell
kubectl port-forward svc/api-service 8000:80 -n reservainteligente
```

Luego abres:

```text
http://localhost:8000/docs
```

Ahí puedes probar rutas como:

```text
- GET /restaurants/
- GET /users/me
- GET /restaurants/{restaurant_id}
- GET /users/
```


## Orden recomendado para inicialiazar

```text
1. .\deploy-all.ps1    (desplegar todo)
2. .\status.ps1        (verificar que esta corriendo)
3. .\cleanup-all.ps1   (cuando termines de trabajar)
4. .\deploy-all.ps1    (volver a desplegar si lo necesitas)
```


