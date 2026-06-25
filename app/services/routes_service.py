"""
app/services/routes_service.py
──────────────────────────────
Servicio de rutas de entrega optimizadas.

Lee los pedidos a domicilio desde Neo4J y calcula el orden optimo
de entrega para cada repartidor usando el algoritmo de vecino mas cercano.
"""

from app.database.neo4j import get_neo4j_driver

# Matriz de distancias entre zonas. Se llena en runtime desde el grafo de Neo4J
# (cargar_matriz_distancias) usando shortestPath sobre las relaciones DISTANCIA_A,
# asi se obtiene la distancia minima real entre cualquier par de zonas (incluso
# las que no tienen arista directa, via caminos multi-salto) en vez de un
# diccionario fijo e incompleto.
DISTANCIAS: dict[tuple[str, str], int] = {}

def cargar_matriz_distancias() -> None:
    """Calcula la distancia minima en km entre todos los pares de zonas con shortestPath."""
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run("""
            MATCH (a:Zona), (b:Zona)
            WHERE a.nombre < b.nombre
            MATCH p = shortestPath((a)-[:DISTANCIA_A*]-(b))
            RETURN a.nombre AS za, b.nombre AS zb,
                   reduce(s = 0, r IN relationships(p) | s + r.km) AS km
        """)
        for row in result:
            DISTANCIAS[(row["za"], row["zb"])] = row["km"]

def distancia_entre_zonas(zona_a: str, zona_b: str) -> int:
    """Devuelve la distancia minima en km entre dos zonas (de la matriz cargada del grafo)."""
    if zona_a == zona_b:
        return 0
    return DISTANCIAS.get((zona_a, zona_b),
           DISTANCIAS.get((zona_b, zona_a), 999))

def vecino_mas_cercano(zona_inicio: str, pedidos: list[dict]) -> tuple[list[dict], int]:
    """
    Algoritmo de vecino mas cercano para optimizar el orden de entrega.

    Parametros:
      zona_inicio: zona del restaurante (punto de partida del repartidor)
      pedidos: lista de pedidos con zona_entrega

    Retorna:
      ruta: pedidos ordenados de forma optima
      km_total: distancia total recorrida
    """
    pendientes  = pedidos.copy()
    ruta        = []
    zona_actual = zona_inicio
    km_total    = 0

    while pendientes:
        mas_cercano = min(
            pendientes,
            key=lambda p: distancia_entre_zonas(zona_actual, p["zona_entrega"] or zona_inicio)
        )
        km          = distancia_entre_zonas(zona_actual, mas_cercano["zona_entrega"] or zona_inicio)
        km_total   += km
        zona_actual = mas_cercano["zona_entrega"] or zona_inicio

        ruta.append({**mas_cercano, "km_desde_anterior": km})
        pendientes.remove(mas_cercano)

    return ruta, km_total

def obtener_pedidos_pendientes() -> list[dict]:
    """Lee los pedidos a domicilio PENDIENTES de entrega desde Neo4J.

    Solo estados aun no finalizados (pendiente, confirmado, en_preparacion, listo);
    se excluyen 'entregado' y 'cancelado' porque no tiene sentido rutear un pedido
    que ya se entrego o que se cancelo.
    """
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run("""
            MATCH (u:Usuario)-[:REALIZO]->(o:Pedido)-[:EN]->(r:Restaurante)
            WHERE toUpper(o.tipo_entrega) = 'DOMICILIO'
              AND toUpper(o.estado) IN ['PENDIENTE', 'CONFIRMADO', 'EN_PREPARACION', 'LISTO']
            RETURN o.id            AS pedido_id,
                   u.nombre        AS cliente,
                   o.zona_entrega  AS zona_entrega,
                   r.nombre        AS restaurante,
                   r.zona          AS zona_restaurante,
                   o.total         AS total,
                   o.estado        AS estado
            ORDER BY o.fecha ASC
        """)
        return [dict(r) for r in result]

def calcular_rutas(num_repartidores: int = 2) -> dict:
    """
    Calcula las rutas optimas para todos los repartidores.

    Parametros:
      num_repartidores: cantidad de repartidores disponibles

    Retorna:
      dict con las rutas por repartidor y estadisticas
    """
    cargar_matriz_distancias()
    pedidos = obtener_pedidos_pendientes()

    if not pedidos:
        return {
            "total_pedidos": 0,
            "repartidores": [],
            "mensaje": "No hay pedidos a domicilio disponibles"
        }

    # Agrupar pedidos por restaurante
    por_restaurante: dict[str, dict] = {}
    for p in pedidos:
        rest = p["restaurante"]
        if rest not in por_restaurante:
            por_restaurante[rest] = {
                "zona_restaurante": p["zona_restaurante"],
                "pedidos": []
            }
        por_restaurante[rest]["pedidos"].append(p)

    # Distribuir restaurantes entre repartidores (round-robin)
    asignaciones: dict[str, list] = {f"Repartidor {i+1}": [] for i in range(num_repartidores)}
    repartidores = list(asignaciones.keys())

    for i, (restaurante, datos) in enumerate(por_restaurante.items()):
        repartidor = repartidores[i % num_repartidores]
        asignaciones[repartidor].append({
            "restaurante":      restaurante,
            "zona_restaurante": datos["zona_restaurante"],
            "pedidos":          datos["pedidos"]
        })

    # Calcular ruta optima para cada repartidor
    resultado_repartidores = []
    for repartidor, grupos in asignaciones.items():
        paradas = []
        km_total_repartidor = 0

        for grupo in grupos:
            ruta, km = vecino_mas_cercano(grupo["zona_restaurante"], grupo["pedidos"])
            km_total_repartidor += km
            paradas.append({
                "restaurante":      grupo["restaurante"],
                "zona_restaurante": grupo["zona_restaurante"],
                "entregas":         ruta,
                "km_restaurante":   km
            })

        resultado_repartidores.append({
            "repartidor":   repartidor,
            "paradas":      paradas,
            "km_total":     km_total_repartidor,
            "total_pedidos": sum(len(p["entregas"]) for p in paradas)
        })

    return {
        "total_pedidos":    len(pedidos),
        "num_repartidores": num_repartidores,
        "algoritmo":        "Vecino Más Cercano",
        "repartidores":     resultado_repartidores
    }
