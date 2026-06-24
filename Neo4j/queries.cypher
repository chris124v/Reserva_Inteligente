// ═══════════════════════════════════════════════════════════════════════════════
// neo4j/queries.cypher
// Consultas Cypher — Reserva Inteligente
// Ejecutar en Neo4J Browser: http://localhost:7474
// (con port-forward activo: kubectl port-forward svc/neo4j-service 7474:7474 7687:7687 -n reservainteligente)
// ═══════════════════════════════════════════════════════════════════════════════


// ── 1. Los 5 productos más comprados juntos (co-compras) ─────────────────────
// Busca pares de productos que aparecen en el mismo pedido.
// Útil para recomendaciones: "los clientes que piden X también piden Y"

MATCH (p1:Producto)<-[:CONTIENE]-(o:Pedido)-[:CONTIENE]->(p2:Producto)
WHERE p1.id < p2.id
  AND o.estado <> 'cancelado'
WITH p1.nombre AS producto_1,
     p2.nombre AS producto_2,
     count(o)  AS veces_juntos
ORDER BY veces_juntos DESC
LIMIT 5
RETURN producto_1, producto_2, veces_juntos;


// ── 2. Usuarios más influyentes por actividad ────────────────────────────────
// Identifica los usuarios con mayor actividad: más pedidos realizados
// y mayor gasto total. Son los "usuarios influyentes" del sistema.

MATCH (u:Usuario)-[:REALIZO]->(o:Pedido)
WITH u.nombre      AS usuario,
     u.email       AS email,
     count(o)      AS total_pedidos,
     sum(o.total)  AS gasto_total
ORDER BY total_pedidos DESC
RETURN usuario, email, total_pedidos, round(gasto_total) AS gasto_total_CRC;


// ── 3. Usuarios que recomiendan a otros (red de referidos) ───────────────────
// Recorre la relación (Usuario)-[:RECOMENDO]->(Usuario) y rankea a los usuarios
// que trajeron más clientes nuevos al sistema. Son los "usuarios que recomiendan
// a otros" del Req 5. Devuelve cuántos referidos directos tiene cada uno.

MATCH (u:Usuario)-[:RECOMENDO]->(referido:Usuario)
RETURN u.nombre                     AS usuario,
       u.email                      AS email,
       count(referido)              AS usuarios_recomendados,
       collect(referido.nombre)[..5] AS algunos_referidos
ORDER BY usuarios_recomendados DESC
LIMIT 10;


// ── 3b. Alcance total de un recomendador (referidos en cadena) ───────────────
// No solo los referidos directos, sino toda la cadena de invitaciones que parte
// de un usuario (referidos de sus referidos, etc.). Mide influencia real.

MATCH (u:Usuario)-[:RECOMENDO*1..]->(alcanzado:Usuario)
WITH u.nombre AS usuario, count(DISTINCT alcanzado) AS alcance_total
ORDER BY alcance_total DESC
LIMIT 10
RETURN usuario, alcance_total;


// ── 4. Camino mínimo entre dos zonas (ruta de entrega) ───────────────────────
// Calcula la ruta más corta en km entre dos zonas.
// Cambiar los nombres de zona según la ruta que se quiera calcular.

MATCH path = shortestPath(
    (origen:Zona {nombre: "Calle Roma"})-[:DISTANCIA_A*]->(destino:Zona {nombre: "Muelle"})
)
RETURN [n IN nodes(path) | n.nombre]                          AS ruta,
       reduce(dist = 0, r IN relationships(path) | dist + r.km) AS km_total;


// ── 5. Todas las rutas desde una zona ordenadas por distancia ────────────────
// Muestra todos los destinos posibles desde una zona de origen,
// ordenados de más cercano a más lejano. Útil para asignar repartidores.

MATCH path = (origen:Zona {nombre: "Calle Roma"})-[:DISTANCIA_A*1..4]->(destino:Zona)
WHERE origen <> destino
WITH destino.nombre AS zona_destino,
     [n IN nodes(path) | n.nombre]                               AS ruta,
     reduce(dist = 0, r IN relationships(path) | dist + r.km)   AS km_total
ORDER BY km_total ASC
RETURN zona_destino, ruta, km_total
LIMIT 20;


// ── 6. Cola de pedidos pendientes para repartidores ──────────────────────────
// Muestra pedidos a domicilio pendientes de entrega con la zona del cliente y
// el restaurante de origen. Entrada del módulo de rutas (rutas_entrega.py).

MATCH (u:Usuario)-[:REALIZO]->(o:Pedido)-[:EN]->(r:Restaurante)
WHERE o.estado IN ['pendiente', 'confirmado', 'en_preparacion', 'listo']
  AND o.tipo_entrega = 'domicilio'
RETURN u.nombre          AS cliente,
       o.id              AS pedido_id,
       r.nombre          AS restaurante,
       r.zona            AS zona_origen,
       o.total           AS total_CRC
ORDER BY o.fecha ASC;


// ── 7. Productos más vendidos por restaurante ────────────────────────────────

MATCH (r:Restaurante)<-[:EN]-(o:Pedido)-[:CONTIENE]->(p:Producto)
WHERE o.estado <> 'cancelado'
WITH r.nombre    AS restaurante,
     p.nombre    AS producto,
     p.categoria AS categoria,
     count(o)    AS veces_pedido
ORDER BY restaurante, veces_pedido DESC
RETURN restaurante, producto, categoria, veces_pedido;


// ── 8. Ingresos por restaurante ──────────────────────────────────────────────

MATCH (o:Pedido)-[:EN]->(r:Restaurante)
WHERE o.estado = 'entregado'
WITH r.nombre   AS restaurante,
     r.zona     AS zona,
     count(o)   AS pedidos_completados,
     sum(o.total) AS ingresos_totales
ORDER BY ingresos_totales DESC
RETURN restaurante, zona, pedidos_completados,
       round(ingresos_totales) AS ingresos_CRC;


// ── 9. Verificar estructura completa del grafo ───────────────────────────────

MATCH (n) RETURN labels(n) AS tipo, count(n) AS cantidad ORDER BY cantidad DESC;

MATCH ()-[r]->() RETURN type(r) AS relacion, count(r) AS cantidad ORDER BY cantidad DESC;
