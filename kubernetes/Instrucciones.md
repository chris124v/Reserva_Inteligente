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
---

## 1. Desplegar stack operacional (deploy-all.ps1)

```powershell
.\deploy-all.ps1
```
Despliega todo: namespace, configuracion, bases de datos y API.

---

## 2. Desplegar OLAP + Spark + Airflow + Metabase (deploy-olap.ps1)

Requiere que el stack operacional ya este corriendo (paso 1).

```powershell
.\deploy-olap.ps1
```

Despliega en orden:

1. HDFS NameNode
2. HDFS DataNode
3. Hive (ConfigMap + Metastore DB + Metastore + HiveServer2)
4. Spark Master + Worker
5. Inicializa el esquema estrella en Hive (`schema_estrella.hql`) y aplica el seed de PostgreSQL
6. Airflow (invoca `deploy-airflow.ps1`): ConfigMap/Secret → Airflow Postgres → init job (db migrate + usuario admin) → Scheduler → Webserver
7. Metabase (invoca `deploy-metabase.ps1`): PV/PVC → Deployment → Service

Tambien se puede correr cada capa por separado:

```powershell
.\deploy-airflow.ps1
.\deploy-metabase.ps1
```

Detalle de verificacion, logs y port-forwards de cada componente en las secciones 15 a 21 de este documento.

---

## 3. Estado (status.ps1)

```powershell
.\status.ps1
```
Verifica el estado del ambiente completo.

---

## 4. Limpiar (cleanup-all.ps1)


Elimina todos los recursos. Pide confirmacion antes por si las dudas. Ese primer execution policy es por si no funciona con un solo comando.

```powershell

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
powershell -ExecutionPolicy Bypass -File .\cleanup-all.ps1

.\cleanup-all.ps1
```

---

## 5. Ver datos del Sistema

Aqui vemos pods, services y pvcs

``` powershell
kubectl get pods -n reservainteligente
kubectl get svc -n reservainteligente
kubectl get pvc -n reservainteligente
kubectl get all -n reservainteligente
```

---

## 6. Ver logs para debug

Tanto para todos como para un pod especifico

``` powershell
kubectl logs -l app=main-api -n reservainteligente
kubectl logs <nombre-pod> -n reservainteligente
kubectl describe pod <nombre-pod> -n reservainteligente
kubectl describe deployment main-api -n reservainteligente
```

---

## 7. API

Algunos comando importantes para el despliegue de la api

``` powershell
kubectl rollout restart deployment/main-api -n reservainteligente #Reiniciar la api
kubectl port-forward svc/api-service 8000:80 -n reservainteligente #Forward local de la api
kubectl logs -f -l app=main-api -n reservainteligente #Ver logs
```

---

## 8. Mongo

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

---

## 9. Postgres

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

---

## 10. Aplicar cambios a configs

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

---

## 11. Redis

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

--=

## 11. Elastic Search Comandos

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

---

## 12. Search Service (Microservicio)

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

---

## 13. Nginx Load Balancer

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

---

## 14. Escalabilidad con KS

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

---


## 15. OLAP (vision general)

Estado de todos los pods de la capa analitica (OLAP + Spark + Airflow + Metabase)

```powershell
kubectl get pods -n reservainteligente -l "app in (hdfs-namenode,hdfs-datanode,hive-metastore-db,hive-metastore,hiveserver2,spark-master,spark-worker,airflow-postgres,airflow-scheduler,airflow-webserver,metabase)"
```

Script de estado completo (incluye las 9 capas: cluster, namespace, operacional, HDFS, Hive, Spark, Airflow, Metabase, PVC)

```powershell
.\status.ps1
```

Volver a desplegar toda la capa OLAP desde cero

```powershell
.\deploy-olap.ps1
```

Detener solo la capa OLAP sin tocar el stack operacional (usa cleanup-all.ps1 y luego vuelves a levantar solo el paso 1)

```powershell
.\cleanup-all.ps1
```

---

## 16. Hive

Estado de los pods de Hive

```powershell
kubectl get pods -n reservainteligente -l "app in (hive-metastore-db,hive-metastore,hiveserver2)"
```

Logs Hive Metastore

```powershell
kubectl logs -n reservainteligente -l app=hive-metastore --tail=20
kubectl logs -n reservainteligente -l app=hive-metastore -c init-schema --tail=20
```

Logs HiveServer2

```powershell
kubectl logs -n reservainteligente -l app=hiveserver2 --tail=20
```

Verificar el esquema estrella (base de datos `reserva_dw`, tablas y vistas)

```powershell
$hivePod = kubectl get pods -n reservainteligente -l app=hiveserver2 -o jsonpath='{.items[0].metadata.name}'
kubectl exec -n reservainteligente $hivePod -- /opt/hive/bin/hive -e "USE reserva_dw; SHOW TABLES;"
kubectl exec -n reservainteligente $hivePod -- /opt/hive/bin/hive -e "USE reserva_dw; SELECT COUNT(*) FROM fact_reservas;"
kubectl exec -n reservainteligente $hivePod -- /opt/hive/bin/hive -e "USE reserva_dw; SELECT COUNT(*) FROM fact_pedidos;"
```

Re-aplicar el DDL manualmente si hace falta

```powershell
kubectl exec -i -n reservainteligente $hivePod -- sh -c "cat > /tmp/schema_estrella.hql" < ..\olap\hive\schema_estrella.hql
kubectl exec -n reservainteligente $hivePod -- /opt/hive/bin/hive -f /tmp/schema_estrella.hql
```

Web UI HiveServer2 (ver queries activas)

```powershell
kubectl port-forward -n reservainteligente svc/hiveserver2 10002:10002
# http://localhost:10002
```

JDBC (por si se quiere conectar un cliente externo, ej. DBeaver)

```powershell
kubectl port-forward -n reservainteligente svc/hiveserver2 10000:10000
# jdbc:hive2://localhost:10000
```

---

## 17. HDFS

Estado de los pods de HDFS

```powershell
kubectl get pods -n reservainteligente -l "app in (hdfs-namenode,hdfs-datanode)"
```

Logs HDFS NameNode

```powershell
kubectl logs -n reservainteligente hdfs-namenode-0 --tail=20
```

Logs HDFS DataNode

```powershell
kubectl logs -n reservainteligente hdfs-datanode-0 --tail=20
```

Ver el estado del filesystem y datanodes registrados

```powershell
kubectl exec -n reservainteligente hdfs-namenode-0 -- hdfs dfsadmin -report
kubectl exec -n reservainteligente hdfs-namenode-0 -- hdfs dfs -ls /
```

Web UI HDFS (ver cluster, bloques y archivos)

```powershell
kubectl port-forward -n reservainteligente svc/hdfs-namenode 9870:9870
# http://localhost:9870
```

---

## 18. Spark

Estado de los pods de Spark

```powershell
kubectl get pods -n reservainteligente -l "app in (spark-master,spark-worker)"
```

Logs

```powershell
kubectl logs -n reservainteligente -l app=spark-master --tail=20
kubectl logs -n reservainteligente -l app=spark-worker --tail=20
```

Web UI Spark Master (ver jobs y workers)

```powershell
kubectl port-forward -n reservainteligente svc/spark-master 8080:8080
# http://localhost:8080
```

Ejecutar los analisis de Spark manualmente (no es necesario si ya corre el DAG de Airflow, que los ejecuta dentro del propio contenedor de Airflow)

```powershell
$pod = kubectl get pods -n reservainteligente -l app=spark-master -o jsonpath='{.items[0].metadata.name}'

kubectl cp ..\olap\spark\tendencias_consumo.py reservainteligente/${pod}:/tmp/
kubectl cp ..\olap\spark\horarios_pico.py reservainteligente/${pod}:/tmp/
kubectl cp ..\olap\spark\crecimiento_mensual.py reservainteligente/${pod}:/tmp/
kubectl cp ..\olap\spark\etl_dimensiones_hechos.py reservainteligente/${pod}:/tmp/
kubectl cp ..\olap\spark\materializar_vistas_metabase.py reservainteligente/${pod}:/tmp/

kubectl exec -n reservainteligente $pod -- bash -c "PYSPARK_PYTHON=python3 PYSPARK_DRIVER_PYTHON=python3 /spark/bin/spark-submit --master 'local[*]' --packages org.postgresql:postgresql:42.7.1 /tmp/tendencias_consumo.py"
kubectl exec -n reservainteligente $pod -- bash -c "PYSPARK_PYTHON=python3 PYSPARK_DRIVER_PYTHON=python3 /spark/bin/spark-submit --master 'local[*]' --packages org.postgresql:postgresql:42.7.1 /tmp/horarios_pico.py"
kubectl exec -n reservainteligente $pod -- bash -c "PYSPARK_PYTHON=python3 PYSPARK_DRIVER_PYTHON=python3 /spark/bin/spark-submit --master 'local[*]' --packages org.postgresql:postgresql:42.7.1 /tmp/crecimiento_mensual.py"
```

Resultados en PostgreSQL: `analytics_tendencias_consumo`, `analytics_horarios_pico`, `analytics_crecimiento_mensual` (Req 2), y `analytics_ingresos_mes_categoria`, `analytics_actividad_zona`, `analytics_pedidos_estado` (Req 3, materializados por `materializar_vistas_metabase.py`).

```powershell
$pgPod = kubectl get pods -n reservainteligente -l app=postgres -o jsonpath='{.items[0].metadata.name}'
kubectl exec -n reservainteligente $pgPod -- psql -U postgres -d restaurantes_db -c "SELECT * FROM analytics_tendencias_consumo LIMIT 5;"
```

---

## 19. Airflow

Estado de los pods de Airflow

```powershell
kubectl get pods -n reservainteligente -l "app in (airflow-postgres,airflow-scheduler,airflow-webserver)"
kubectl get job airflow-init -n reservainteligente
```

Desplegar/redesplegar solo Airflow

```powershell
.\deploy-airflow.ps1
```

Logs

```powershell
kubectl logs -n reservainteligente -l app=airflow-scheduler --tail=50
kubectl logs -n reservainteligente -l app=airflow-webserver --tail=50
kubectl logs -n reservainteligente job/airflow-init --tail=50
```

Web UI Airflow (usuario/clave definidos en `airflow-secret.yaml`)

```powershell
kubectl port-forward -n reservainteligente svc/airflow-webserver 8080:8080
# http://localhost:8080
```

Ver y disparar el DAG desde la CLI dentro del pod del scheduler

```powershell
$schedPod = kubectl get pods -n reservainteligente -l app=airflow-scheduler -o jsonpath='{.items[0].metadata.name}'

kubectl exec -n reservainteligente $schedPod -- airflow dags list
kubectl exec -n reservainteligente $schedPod -- airflow dags trigger etl_reserva_dw
kubectl exec -n reservainteligente $schedPod -- airflow tasks states-for-dag-run etl_reserva_dw <run_id>
```

Ver/editar la Variable que controla la deteccion de cambios en el catalogo (usada por `verificar_cambio_catalogo`)

```powershell
kubectl exec -n reservainteligente $schedPod -- airflow variables get ultima_actualizacion_catalogo
kubectl exec -n reservainteligente $schedPod -- airflow variables set ultima_actualizacion_catalogo "2000-01-01T00:00:00"
```

Forzar la rama de reindexado (provoca que `verificar_cambio_catalogo` detecte cambio y dispare `reindexar_elasticsearch` en la siguiente corrida)

```powershell
$pgPod = kubectl get pods -n reservainteligente -l app=postgres -o jsonpath='{.items[0].metadata.name}'
kubectl exec -n reservainteligente $pgPod -- psql -U postgres -d restaurantes_db -c "UPDATE menus SET fecha_actualizacion = NOW() WHERE id = (SELECT id FROM menus LIMIT 1);"
kubectl exec -n reservainteligente $schedPod -- airflow dags trigger etl_reserva_dw
```

Actualizar la imagen de Airflow despues de un commit (jalar el `:latest` nuevo de GHCR)

> IMPORTANTE: en este cluster de un solo nodo NO uses `kubectl rollout restart`
> para Airflow. El rolling update intenta levantar el pod nuevo antes de matar el
> viejo y el scheduler pide ~1Gi, asi que el pod nuevo se queda en `Pending`
> (`Insufficient memory`) y el rollout se traba. Hay que escalar a 0 primero para
> liberar memoria y luego volver a 1 (esto causa un breve downtime de Airflow, es
> aceptable). `imagePullPolicy: Always` + tag `:latest` hace que el pod nuevo jale
> la imagen recien publicada.

```powershell
# 1) bajar a 0 (libera memoria del nodo)
kubectl scale deployment/airflow-scheduler deployment/airflow-webserver --replicas=0 -n reservainteligente
# esperar a que no queden pods de airflow-scheduler/webserver
kubectl get pods -n reservainteligente -l "app in (airflow-scheduler,airflow-webserver)"

# 2) volver a 1 (crea pods nuevos que jalan el :latest nuevo; tarda ~3 min en jalar la imagen)
kubectl scale deployment/airflow-scheduler deployment/airflow-webserver --replicas=1 -n reservainteligente
kubectl rollout status deployment/airflow-scheduler -n reservainteligente --timeout=300s

# 3) verificar que el pod corre la imagen nueva y el DAG tiene las 4 tasks
$schedPod = kubectl get pods -n reservainteligente -l app=airflow-scheduler -o jsonpath='{.items[0].metadata.name}'
kubectl get pod $schedPod -n reservainteligente -o jsonpath='{.status.containerStatuses[*].imageID}'; Write-Host ""
kubectl exec -n reservainteligente $schedPod -- airflow tasks list etl_reserva_dw
```

---

## 20. Metabase

Estado del pod de Metabase

```powershell
kubectl get pods -n reservainteligente -l app=metabase
```

Desplegar/redesplegar solo Metabase

```powershell
.\deploy-metabase.ps1
```

Logs

```powershell
kubectl logs -n reservainteligente -l app=metabase --tail=50
```

Verificar que existen las tablas analytics_* que alimentan los dashboards (las materializa el DAG de Airflow)

```powershell
$pgPod = kubectl get pods -n reservainteligente -l app=postgres -o jsonpath='{.items[0].metadata.name}'
kubectl exec -n reservainteligente $pgPod -- psql -U postgres -d restaurantes_db -c "SELECT * FROM analytics_ingresos_mes_categoria;"
kubectl exec -n reservainteligente $pgPod -- psql -U postgres -d restaurantes_db -c "SELECT * FROM analytics_actividad_zona;"
kubectl exec -n reservainteligente $pgPod -- psql -U postgres -d restaurantes_db -c "SELECT * FROM analytics_pedidos_estado;"
```

Web UI Metabase (primera vez pide crear el usuario admin)

```powershell
kubectl port-forward -n reservainteligente svc/metabase 3000:3000
# http://localhost:3000
```

Datos para conectar la base de datos en el wizard de Metabase:

- Tipo: PostgreSQL
- Host: `postgres-service`
- Puerto: `5432`
- Base de datos: `restaurantes_db`
- Usuario: `postgres`
- Tablas a usar en los dashboards: `analytics_ingresos_mes_categoria`, `analytics_actividad_zona`, `analytics_pedidos_estado`

---

## 21. Neo4J (Grafos)

Neo4J almacena el grafo de relaciones del sistema: usuarios, restaurantes, productos, pedidos y zonas geograficas.
Se usa para consultas de co-compras, usuarios influyentes, red de referidos y optimizacion de rutas de entrega.

### Desplegar / redesplegar Neo4J

El script aplica los manifiestos, espera que el pod este listo, extrae credenciales de los Secrets de Kubernetes y ejecuta el seed automaticamente.

```powershell
.\deploy-neo4j.ps1
```

Tambien se invoca como ultimo paso de `deploy-olap.ps1`.

Prerequisito: tener el archivo `kubernetes/databases/Neo4j/secret.yaml` creado localmente (esta en `.gitignore`). Ver `secret.example.yaml` como plantilla.

### Estado del pod

```powershell
kubectl get pods -n reservainteligente -l app=neo4j
kubectl get statefulset neo4j -n reservainteligente
```

### Logs

```powershell
kubectl logs -n reservainteligente neo4j-0 --tail=50
kubectl logs -n reservainteligente neo4j-0 -c prepare-conf-and-data --tail=30  # initContainer
```

### Port-forward y Neo4J Browser

```powershell
kubectl port-forward svc/neo4j-service 7474:7474 7687:7687 -n reservainteligente
# http://localhost:7474  (usuario: neo4j, clave: en secret.yaml)
```

### Verificar grafo con cypher-shell

```powershell
kubectl exec -it neo4j-0 -n reservainteligente -- cypher-shell -u neo4j -p Neo4jPass123! "MATCH (n) RETURN labels(n)[0] AS tipo, count(n) AS total ORDER BY total DESC;"
```

Nodos esperados tras el seed: ~566 (39 Usuario, 20 Restaurante, 300 Producto, 200 Pedido, 7 Zona).

### Seed manual (si se necesita recargar el grafo)

```powershell
# Con port-forwards activos (neo4j-service :7687, postgres-service :5432):
kubectl port-forward svc/neo4j-service 7687:7687 -n reservainteligente &
kubectl port-forward svc/postgres-service 5432:5432 -n reservainteligente &

$env:NEO4J_PASSWORD = "Neo4jPass123!"
$env:PG_PASSWORD    = "<clave de postgres>"
pip install -r Neo4j\neo4j-requirements.txt
python Neo4j\seed_neo4j.py
```

### Consultas Cypher (co-compras, recomendaciones, rutas)

Las queries de demostracion estan en `Neo4j\queries.cypher`. Abrirlas con el Neo4J Browser en `http://localhost:7474` o ejecutarlas con `cypher-shell`.

Consultas incluidas:

1. Productos co-comprados con frecuencia
2. Usuarios mas influyentes (mas pedidos realizados)
3. Usuarios que recomendaron a otros (`RECOMENDO` directos)
4. Cadena de alcance por referidos (`RECOMENDO*1..`)
5. Camino mas corto entre dos zonas (`shortestPath`)
6. Todas las rutas desde una zona
7. Cola de pedidos pendientes a domicilio
8. Pedidos por restaurante
9. Productos mas pedidos globalmente

### Simular rutas de entrega (vecino mas cercano)

```powershell
kubectl port-forward svc/neo4j-service 7687:7687 -n reservainteligente
$env:NEO4J_PASSWORD = "Neo4jPass123!"
python Neo4j\rutas_entrega.py
```

Genera `Neo4j\rutas_resultado.json` con el orden optimo de entregas por repartidor. La matriz de distancias se carga del grafo via `shortestPath` (no hardcodeada).

### Limpiar Neo4J

`cleanup-all.ps1` ya incluye Neo4J (escala el StatefulSet a 0). Para borrarlo manualmente:

```powershell
kubectl scale statefulset/neo4j --replicas=0 -n reservainteligente
kubectl delete statefulset/neo4j -n reservainteligente
kubectl delete svc/neo4j-service -n reservainteligente
kubectl delete configmap/neo4j-config -n reservainteligente
kubectl delete secret/neo4j-secret -n reservainteligente
kubectl delete pvc/neo4j-storage-neo4j-0 -n reservainteligente
```
