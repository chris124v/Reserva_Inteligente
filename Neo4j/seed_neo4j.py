"""
neo4j/seed_neo4j.py
────────────────────
Lee los datos de PostgreSQL y los carga en Neo4J como grafo.

Nodos:
  (:Usuario)      — clientes y admins del sistema
  (:Restaurante)  — restaurantes registrados
  (:Producto)     — items de menu
  (:Pedido)       — pedidos realizados
  (:Zona)         — zonas geograficas (para rutas de entrega)

Relaciones:
  (Usuario)-[:REALIZO]->(Pedido)
  (Pedido)-[:EN]->(Restaurante)
  (Pedido)-[:CONTIENE {cantidad}]->(Producto)
  (Producto)-[:PERTENECE_A]->(Restaurante)
  (Restaurante)-[:UBICADO_EN]->(Zona)
  (Zona)-[:DISTANCIA_A {km}]->(Zona)

Uso (con port-forward activo):
  kubectl port-forward svc/neo4j-service 7687:7687 -n reservainteligente
  kubectl port-forward svc/postgres-service 5432:5432 -n reservainteligente
  pip install neo4j psycopg2-binary
  python neo4j/seed_neo4j.py
"""

import os
import psycopg2
import random
import json
from neo4j import GraphDatabase

# ── Configuracion ─────────────────────────────────────────────────────────────
# Credenciales por variable de entorno (no hardcodeadas). El script de despliegue
# (deploy-neo4j.ps1) las extrae de los Secrets de Kubernetes antes de correr esto.
# Para correr manual: setear PG_PASSWORD y NEO4J_PASSWORD en el entorno.
# Host localhost porque se accede via port-forward de Kubernetes.
PG_CONFIG = {
    "host":     os.environ.get("PG_HOST", "localhost"),
    "port":     int(os.environ.get("PG_PORT", "5432")),
    "dbname":   os.environ.get("PG_DBNAME", "restaurantes_db"),
    "user":     os.environ.get("PG_USER", "postgres"),
    "password": os.environ.get("PG_PASSWORD", "postgres"),
}

NEO4J_URI      = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER     = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "neo4j")

# ── Zonas y distancias para rutas de entrega ──────────────────────────────────
# Zonas extraidas de las direcciones de los restaurantes del seed
ZONAS = [
    "Calle Roma",
    "Av Italia",
    "Calle Falsa",
    "Muelle",
    "Boulevard",
    "Av Gol",
    "Plaza Central",
]

# Distancias aproximadas en km entre zonas (para simular rutas de entrega)
DISTANCIAS = {
    ("Calle Roma",    "Av Italia"):      2,
    ("Calle Roma",    "Calle Falsa"):    3,
    ("Calle Roma",    "Muelle"):         8,
    ("Calle Roma",    "Boulevard"):      5,
    ("Calle Roma",    "Av Gol"):         4,
    ("Calle Roma",    "Plaza Central"):  1,
    ("Av Italia",     "Calle Falsa"):    2,
    ("Av Italia",     "Muelle"):         7,
    ("Av Italia",     "Boulevard"):      4,
    ("Calle Falsa",   "Muelle"):         6,
    ("Calle Falsa",   "Av Gol"):         3,
    ("Muelle",        "Boulevard"):      4,
    ("Boulevard",     "Av Gol"):         2,
    ("Av Gol",        "Plaza Central"):  3,
    ("Plaza Central", "Calle Falsa"):    2,
}

def extraer_zona(direccion):
    """Extrae la zona de la direccion del restaurante."""
    if not direccion:
        return "Plaza Central"
    for zona in ZONAS:
        if zona.lower() in direccion.lower():
            return zona
    return "Plaza Central"

# ── Funciones de carga ────────────────────────────────────────────────────────

def limpiar_grafo(session):
    print("  Limpiando grafo anterior...")
    session.run("MATCH (n) DETACH DELETE n")

def crear_zonas(session):
    print("  Creando nodos Zona...")
    for zona in ZONAS:
        session.run("MERGE (:Zona {nombre: $nombre})", nombre=zona)

    print("  Creando relaciones DISTANCIA_A...")
    for (z1, z2), km in DISTANCIAS.items():
        session.run("""
            MATCH (a:Zona {nombre: $z1}), (b:Zona {nombre: $z2})
            MERGE (a)-[:DISTANCIA_A {km: $km}]->(b)
            MERGE (b)-[:DISTANCIA_A {km: $km}]->(a)
        """, z1=z1, z2=z2, km=km)

def cargar_usuarios(session, cur):
    print("  Cargando usuarios...")
    cur.execute("SELECT id, nombre, email, rol FROM users ORDER BY id")
    for uid, nombre, email, rol in cur.fetchall():
        session.run("""
            MERGE (u:Usuario {id: $id})
            SET u.nombre = $nombre,
                u.email  = $email,
                u.rol    = $rol
        """, id=uid, nombre=nombre, email=email, rol=rol)

def cargar_restaurantes(session, cur):
    print("  Cargando restaurantes...")
    cur.execute("SELECT id, nombre, direccion FROM restaurants ORDER BY id")
    for rid, nombre, direccion in cur.fetchall():
        zona = extraer_zona(direccion)
        session.run("""
            MERGE (r:Restaurante {id: $id})
            SET r.nombre    = $nombre,
                r.direccion = $direccion,
                r.zona      = $zona
            WITH r
            MATCH (z:Zona {nombre: $zona})
            MERGE (r)-[:UBICADO_EN]->(z)
        """, id=rid, nombre=nombre, direccion=direccion, zona=zona)

def cargar_productos(session, cur):
    print("  Cargando productos (menus)...")
    cur.execute("""
        SELECT id, nombre, precio, categoria, restaurante_id
        FROM menus ORDER BY id
    """)
    for mid, nombre, precio, categoria, rest_id in cur.fetchall():
        session.run("""
            MERGE (p:Producto {id: $id})
            SET p.nombre    = $nombre,
                p.precio    = $precio,
                p.categoria = $categoria
            WITH p
            MATCH (r:Restaurante {id: $rest_id})
            MERGE (p)-[:PERTENECE_A]->(r)
        """, id=mid, nombre=nombre, precio=float(precio),
             categoria=categoria or "general", rest_id=rest_id)

def cargar_pedidos(session, cur):
    print("  Cargando pedidos y relaciones CONTIENE...")

    # Obtener zonas de restaurantes para asignar zonas distintas a pedidos domicilio
    cur.execute("SELECT id, direccion FROM restaurants")
    zona_por_restaurante = {rid: extraer_zona(dir) for rid, dir in cur.fetchall()}

    cur.execute("""
        SELECT id, usuario_id, restaurante_id, items, total,
               estado, tipo_entrega, fecha_creacion
        FROM orders ORDER BY id
    """)
    for oid, uid, rid, items_raw, total, estado, tipo, fecha in cur.fetchall():
        items = items_raw if isinstance(items_raw, list) else json.loads(items_raw)

        # Postgres guarda estado/tipo_entrega en MAYUSCULA (enums SQLAlchemy), pero
        # todas las consultas Cypher comparan en minuscula. Normalizamos aqui para
        # que los filtros (estado <> 'cancelado', tipo_entrega = 'domicilio', etc.)
        # funcionen de forma consistente en el grafo.
        estado_norm = (estado or "").lower()
        tipo_norm   = (tipo or "").lower()

        # Asignar zona de entrega distinta a la del restaurante para pedidos a domicilio
        zona_rest = zona_por_restaurante.get(rid, ZONAS[0])
        if tipo_norm == "domicilio":
            zonas_disponibles = [z for z in ZONAS if z != zona_rest]
            zona_entrega = random.choice(zonas_disponibles)
        else:
            zona_entrega = None

        session.run("""
            MERGE (o:Pedido {id: $id})
            SET o.total        = $total,
                o.estado       = $estado,
                o.tipo_entrega = $tipo,
                o.zona_entrega = $zona_entrega,
                o.fecha        = $fecha
            WITH o
            MATCH (u:Usuario     {id: $uid})
            MATCH (r:Restaurante {id: $rid})
            MERGE (u)-[:REALIZO]->(o)
            MERGE (o)-[:EN]->(r)
        """, id=oid, total=float(total), estado=estado_norm,
             tipo=tipo_norm, zona_entrega=zona_entrega, fecha=str(fecha), uid=uid, rid=rid)

        # Relacion CONTIENE por cada producto del pedido
        for item in items:
            session.run("""
                MATCH (o:Pedido   {id: $oid})
                MATCH (p:Producto {id: $pid})
                MERGE (o)-[c:CONTIENE]->(p)
                ON CREATE SET c.cantidad = $cantidad
                ON MATCH  SET c.cantidad = c.cantidad + $cantidad
            """, oid=oid, pid=item["menu_id"], cantidad=item["cantidad"])

def crear_recomendaciones(session, cur):
    """
    Crea una red de referidos sintetica: relaciones (Usuario)-[:RECOMENDO]->(Usuario).
    El modelo operacional no tiene datos de referidos, asi que se simula una cadena
    de invitaciones: cada cliente (salvo los primeros "organicos") fue traido al
    sistema por un cliente registrado antes que el. Esto crea "usuarios que
    recomiendan a otros" (Req 5), sobre los que corre la consulta Cypher dedicada.
    """
    print("  Creando red de referidos (RECOMENDO)...")
    cur.execute("SELECT id FROM users WHERE LOWER(rol::text) = 'cliente' ORDER BY id")
    clientes = [row[0] for row in cur.fetchall()]
    if len(clientes) < 2:
        print("    Muy pocos clientes, se omite")
        return

    random.seed(42)  # reproducible entre corridas
    organicos = 5    # los primeros 5 clientes no fueron referidos
    total_refs = 0
    for i, cliente_id in enumerate(clientes[organicos:], start=organicos):
        # 70% de los clientes posteriores fueron referidos por uno anterior
        if random.random() < 0.70:
            referidor = random.choice(clientes[:i])
            session.run("""
                MATCH (a:Usuario {id: $ref}), (b:Usuario {id: $nuevo})
                MERGE (a)-[:RECOMENDO]->(b)
            """, ref=referidor, nuevo=cliente_id)
            total_refs += 1
    print(f"    {total_refs} relaciones RECOMENDO creadas")

def imprimir_estadisticas(session):
    print("\n  Estadisticas del grafo:")
    for label in ["Usuario", "Restaurante", "Producto", "Pedido", "Zona"]:
        result = session.run(f"MATCH (n:{label}) RETURN count(n) AS cnt")
        print(f"    {label}: {result.single()['cnt']}")
    for rel in ["REALIZO", "EN", "CONTIENE", "PERTENECE_A", "UBICADO_EN", "DISTANCIA_A", "RECOMENDO"]:
        result = session.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) AS cnt")
        print(f"    :{rel}: {result.single()['cnt']}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Conectando a PostgreSQL...")
    pg  = psycopg2.connect(**PG_CONFIG)
    cur = pg.cursor()

    print("Conectando a Neo4J...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        limpiar_grafo(session)
        crear_zonas(session)
        cargar_usuarios(session, cur)
        cargar_restaurantes(session, cur)
        cargar_productos(session, cur)
        cargar_pedidos(session, cur)
        crear_recomendaciones(session, cur)
        imprimir_estadisticas(session)

    driver.close()
    pg.close()
    print("\nGrafo Neo4J cargado exitosamente.")

if __name__ == "__main__":
    main()