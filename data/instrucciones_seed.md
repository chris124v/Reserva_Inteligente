# Instrucciones Seed

## Flujo correcto (todo en Kubernetes)

### Si usas PostgreSQL (`DATABASE_TYPE=postgresql`)
1. `python data/seeds/seed_users.py`  ← solo crea usuarios en Cognito
2. Ejecuta cleanup de Postgres (sección 1).
3. Ejecuta seed de Postgres (sección 3) ← crea usuarios + datos en la BD.

### Si usas MongoDB (`DATABASE_TYPE=mongodb`)
1. `python data/seeds/seed_users_mongo.py`  ← solo crea usuarios en Cognito
2. Ejecuta cleanup de Mongo (sección 2).
3. Ejecuta seed de Mongo (sección 4) ← crea usuarios + datos en la BD.

---

## 0. Seed de Usuarios en Cognito

Ambos scripts hacen lo mismo: crear los 10 usuarios en AWS Cognito. Son idempotentes.

```bash
# Si usas PostgreSQL:
python data/seeds/seed_users.py

# Si usas MongoDB:
python data/seeds/seed_users_mongo.py
```

> **Nota:** Los usuarios en las BDs (Postgres/Mongo) los crean `postgres_seed.sql` y
> `mongo_seed.js` directamente. Solo se necesita correr este script una vez por entorno.

## 1. Cleanup Postgres
```bash
psql -h localhost -U postgres -d restaurantes_db -f data/seeds/postgres_cleanup.sql
```

Si Windows no reconoce psql, usa Kubernetes:
```bash
kubectl cp data/seeds/postgres_cleanup.sql reservainteligente/postgres-0:/tmp/postgres_cleanup.sql
kubectl exec -n reservainteligente postgres-0 -- psql -U postgres -d restaurantes_db -f /tmp/postgres_cleanup.sql
```

## 2. Cleanup Mongo
```bash
mongosh --host localhost --port 27017 --file data/seeds/mongo_cleanup.js
```

Si Windows no tiene `mongosh` instalado, usa Kubernetes (recomendado):

```bash
# Copiar script al pod mongos y ejecutarlo
$mpod=$(kubectl get pods -n reservainteligente -l app=mongos -o jsonpath='{.items[0].metadata.name}')
kubectl cp data/seeds/mongo_cleanup.js reservainteligente/${mpod}:/tmp/mongo_cleanup.js
kubectl exec -n reservainteligente ${mpod} -- mongosh --file /tmp/mongo_cleanup.js
```

O, si prefieres no usar Kubernetes, puedes ejecutar el script con un contenedor Mongo local (sin instalar mongosh):

```bash
# Ejecuta desde la carpeta del repo (mapea el archivo y usa la imagen oficial)
docker run --rm -v "%cd%/data/seeds:/scripts" --network host mongo:6.0 mongosh --host localhost --port 27017 --file /scripts/mongo_cleanup.js
```

## 3. Seed Postgres
```bash
psql -h localhost -U postgres -d restaurantes_db -f data/seeds/postgres_seed.sql
```

Si Windows no reconoce psql, usa Kubernetes:
```bash
kubectl cp data/seeds/postgres_seed.sql reservainteligente/postgres-0:/tmp/postgres_seed.sql
kubectl exec -n reservainteligente postgres-0 -- psql -U postgres -d restaurantes_db -f /tmp/postgres_seed.sql
```

## 4. Seed Mongo
```bash
mongosh --host localhost --port 27017 --file data/seeds/mongo_seed.js
```

Si Windows no tiene `mongosh` instalado, usa Kubernetes (recomendado):

```bash
# Copiar script al pod mongos y ejecutarlo
$mpod=$(kubectl get pods -n reservainteligente -l app=mongos -o jsonpath='{.items[0].metadata.name}')
kubectl cp data/seeds/mongo_seed.js reservainteligente/${mpod}:/tmp/mongo_seed.js
kubectl exec -n reservainteligente ${mpod} -- mongosh --file /tmp/mongo_seed.js
```

O, si prefieres no usar Kubernetes, puedes ejecutar el script con un contenedor Mongo local (sin instalar mongosh):

```bash
# Ejecuta desde la carpeta del repo (mapea el archivo y usa la imagen oficial)
docker run --rm -v "%cd%/data/seeds:/scripts" --network host mongo:6.0 mongosh --host localhost --port 27017 --file /scripts/mongo_seed.js
```

## Verificacion rapida
Postgres:
```sql
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM restaurants;
SELECT COUNT(*) FROM menus;
SELECT COUNT(*) FROM reservations;
SELECT COUNT(*) FROM orders;
```

Mongo:
```javascript
db.users.countDocuments();
db.restaurants.countDocuments();
db.menus.countDocuments();
db.reservations.countDocuments();
db.orders.countDocuments();
```

## Nota importante
- Si ejecutas solo seed sin cleanup, puede fallar por datos parciales persistidos.
- Con cleanup + seed, el proceso queda consistente aunque haya quedado data previa.
- Este cleanup de users aplica solo a las BDs locales (Postgres/Mongo), no elimina usuarios en AWS Cognito.
