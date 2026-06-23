"""
app/services/routes_service.py
──────────────────────────────
Servicio de rutas de entrega optimizadas.

Lee los pedidos a domicilio desde Neo4J y calcula el orden optimo
de entrega para cada repartidor usando el algoritmo de vecino mas cercano.
"""

import random
from app.database.neo4j import get_neo4j_driver

# Distancias en km entre zonas del sistema
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

def distancia_entre_zonas(zona_a: str, zona_b: str) -> int:
    """Devuelve la distancia en km entre dos zonas. 999 si no hay conexion directa."""
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
    """Lee los pedidos a domicilio desde Neo4J."""
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run("""
            MATCH (u:Usuario)-[:REALIZO]->(o:Pedido)-[:EN]->(r:Restaurante)
            WHERE toUpper(o.tipo_entrega) = 'DOMICILIO'
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
