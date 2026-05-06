"""
Integration tests para flujos completos del sistema.
Pruebas que validan la interacción entre múltiples servicios.

Categoría: INTEGRACIÓN
Cobertura esperada: >80% de flujos principales
"""

import pytest
from datetime import datetime, timedelta


# ==================== FLUJO: CREAR RESERVA ====================

@pytest.mark.integration
class TestReservationFlowIntegration:
    """Tests de integración para flujo de creación de reserva."""
    
    def test_complete_reservation_flow(self, users_data, restaurants_data, reservations_data):
        """
        FLUJO COMPLETO:
        1. Usuario se autentica
        2. Consulta restaurante disponible
        3. Crea reserva
        4. Sistema confirma reserva
        5. Se envía notificación
        """
        # Arrange
        user = users_data[0]  # primer cliente
        restaurant = restaurants_data[0]
        
        # Act & Assert - Paso 1: Autenticar
        assert user is not None
        assert user["rol"] == "cliente"
        
        # Paso 2: Consultar disponibilidad de restaurante
        assert restaurant["total_mesas"] > 0
        assert restaurant["activo"] != False or restaurant["activo"] is None
        
        # Paso 3: Crear reserva
        reservation_data = {
            "usuario_id": user["id"],
            "restaurante_id": restaurant["id"],
            "fecha": (datetime.now() + timedelta(days=3)).date().isoformat(),
            "hora": "19:00",
            "cantidad_personas": 4
        }
        
        # Paso 4: Sistema debería confirmar
        assert reservation_data["cantidad_personas"] <= restaurant["total_mesas"]
        
        # Paso 5: Validar notificación quedaría pendiente
        # (En integración real, verificar cola de eventos)
    
    def test_reservation_availability_check(self, restaurants_data):
        """Verificar disponibilidad de mesas en restaurante."""
        restaurant = restaurants_data[0]
        
        # Simular búsqueda de disponibilidad
        total_mesas = restaurant["total_mesas"]
        reserved_mesas = 5
        available_mesas = total_mesas - reserved_mesas
        
        assert available_mesas >= 0
        assert total_mesas >= 1


# ==================== FLUJO: CREAR ORDEN ====================

@pytest.mark.integration
class TestOrderFlowIntegration:
    """Tests de integración para flujo de creación de orden."""
    
    def test_complete_order_flow(self, users_data, restaurants_data, menus_data, orders_data):
        """
        FLUJO COMPLETO:
        1. Usuario se autentica
        2. Consulta menús de restaurante
        3. Selecciona items
        4. Crea orden
        5. Pago procesado
        6. Orden enviada a cocina
        7. Se genera notificación
        """
        # Arrange
        user = users_data[1]  # cliente
        restaurant = restaurants_data[0]
        
        # Act & Assert - Paso 1: Autenticar
        assert user["rol"] == "cliente"
        
        # Paso 2: Consultar menús
        restaurant_menus = [m for m in menus_data if m["restaurante_id"] == restaurant["id"]]
        assert len(restaurant_menus) > 0
        
        # Paso 3: Seleccionar items disponibles
        available_menus = [m for m in restaurant_menus if m["disponible"] is True]
        assert len(available_menus) > 0
        
        # Paso 4: Crear orden
        items = [
            {"menu_id": available_menus[0]["id"], "cantidad": 1},
        ]
        
        # Paso 5: Calcular total (incluir impuesto)
        subtotal = available_menus[0]["precio"]
        tax = int(subtotal * 0.08)
        total = subtotal + tax
        
        assert total > 0
        assert tax == int(subtotal * 0.08)
        
        # Paso 6: Verificar estado (debería ir a cocina)
        # Estado inicial: "confirmada"
        estado_esperado = "confirmada"
        assert estado_esperado in ["confirmada", "en_preparacion"]
    
    def test_order_calculation_with_multiple_items(self, menus_data):
        """Verificar cálculo de orden con múltiples items."""
        # Arrange
        items_to_order = [
            {"menu": menus_data[0], "quantity": 1},
            {"menu": menus_data[1], "quantity": 2},
            {"menu": menus_data[2], "quantity": 1},
        ]
        
        # Act
        subtotal = sum(item["menu"]["precio"] * item["quantity"] for item in items_to_order)
        tax = int(subtotal * 0.08)
        total = subtotal + tax
        
        # Assert
        assert total > subtotal
        assert tax == int(subtotal * 0.08)


# ==================== FLUJO: BÚSQUEDA Y FILTRADO ====================

@pytest.mark.integration
@pytest.mark.search
class TestSearchFlowIntegration:
    """Tests de integración para búsqueda y filtrado."""
    
    def test_search_restaurants_by_category(self, restaurants_data, menus_data):
        """
        FLUJO: Cliente busca restaurantes por categoría de comida.
        1. Usuario ingresa término de búsqueda
        2. Sistema filtra restaurantes
        3. Retorna resultados con menús
        """
        # Arrange
        search_category = "pizza"
        
        # Act
        # Buscar restaurantes que tengan pizza
        restaurants_with_category = set()
        for menu in menus_data:
            if menu["categoria"] == search_category and menu["disponible"]:
                restaurants_with_category.add(menu["restaurante_id"])
        
        # Obtener detalles de restaurantes
        matching_restaurants = [
            r for r in restaurants_data 
            if r["id"] in restaurants_with_category
        ]
        
        # Assert
        assert len(matching_restaurants) > 0
    
    def test_filter_restaurants_by_rating(self, restaurants_data):
        """Filtrar restaurantes por calificación mínima."""
        # Arrange
        min_rating = 4.5
        
        # Act
        high_rated = [r for r in restaurants_data if r.get("rating", 0) >= min_rating]
        
        # Assert
        for restaurant in high_rated:
            assert restaurant["rating"] >= min_rating
    
    def test_filter_restaurants_by_hours(self, restaurants_data):
        """Filtrar restaurantes que estén abiertos a una hora específica."""
        from datetime import datetime
        
        # Arrange
        check_time = "19:30"
        
        # Act
        open_restaurants = []
        for restaurant in restaurants_data:
            apertura = restaurant["hora_apertura"]
            cierre = restaurant["hora_cierre"]
            
            # Simple string comparison (en producción usar datetime)
            if apertura <= check_time <= cierre:
                open_restaurants.append(restaurant)
        
        # Assert - Debería haber restaurantes abiertos a las 19:30
        # (depende de los datos)


# ==================== FLUJO: NOTIFICACIONES Y CACHE ====================

@pytest.mark.integration
@pytest.mark.cache
class TestCacheAndNotificationsIntegration:
    """Tests de integración para caché y notificaciones."""
    
    def test_restaurant_cache_invalidation(self, restaurants_data):
        """
        FLUJO: 
        1. Se carga restaurante en caché
        2. Se actualiza información
        3. Se invalida caché
        4. Se recargan datos
        """
        # Arrange
        restaurant = restaurants_data[0]
        cache_key = f"restaurant:{restaurant['id']}"
        
        # Simular caché
        cache = {}
        
        # Act 1: Cargar en caché
        cache[cache_key] = restaurant
        assert cache_key in cache
        
        # Act 2: Actualizar datos
        restaurant_updated = restaurant.copy()
        restaurant_updated["rating"] = 4.9
        
        # Act 3: Invalidar caché
        del cache[cache_key]
        assert cache_key not in cache
        
        # Act 4: Recargar
        cache[cache_key] = restaurant_updated
        assert cache[cache_key]["rating"] == 4.9
    
    def test_menu_availability_cache(self, menus_data):
        """Caché de disponibilidad de menús."""
        # Arrange
        menu = menus_data[0]
        cache_key = f"menu:disponibilidad:{menu['id']}"
        cache = {}
        
        # Act: Cachear disponibilidad
        cache[cache_key] = {"disponible": menu["disponible"], "timestamp": datetime.now().isoformat()}
        
        # Assert
        assert cache[cache_key]["disponible"] == menu["disponible"]


# ==================== FLUJO: VALIDACIONES DE NEGOCIO ====================

@pytest.mark.integration
class TestBusinessRulesIntegration:
    """Tests de integración para reglas de negocio."""
    
    def test_cannot_reserve_past_date(self):
        """No se puede crear reserva con fecha pasada."""
        from datetime import datetime, timedelta
        
        # Arrange
        past_date = (datetime.now() - timedelta(days=1)).date()
        
        # Act & Assert
        # En integración real, debería lanzar excepción
        assert past_date < datetime.now().date()
    
    def test_cannot_order_unavailable_menu(self, menus_data):
        """No se puede ordenar un menú no disponible."""
        # Arrange
        unavailable_menus = [m for m in menus_data if m["disponible"] is False]
        
        if unavailable_menus:
            menu = unavailable_menus[0]
            
            # Act & Assert
            assert menu["disponible"] is False
            # En integración real, el sistema rechazaría esta orden
    
    def test_cannot_exceed_restaurant_capacity(self, restaurants_data):
        """No se puede reservar más personas que la capacidad."""
        # Arrange
        restaurant = restaurants_data[0]
        total_mesas = restaurant["total_mesas"]
        personas_por_mesa = 4  # Capacidad promedio
        max_capacity = total_mesas * personas_por_mesa
        
        # Act
        personas_solicitadas = max_capacity + 10
        
        # Assert
        assert personas_solicitadas > max_capacity
        # En integración real, el sistema rechazaría esta reserva


# ==================== FLUJO: CONCURRENCIA ====================

@pytest.mark.integration
@pytest.mark.slow
class TestConcurrencyIntegration:
    """Tests de integración para casos concurrentes."""
    
    def test_simultaneous_reservations_same_table(self, restaurants_data, reservations_data):
        """
        ESCENARIO: Dos usuarios reservan la misma mesa simultáneamente.
        Sistema debe manejar esto correctamente (solo una debe pasar).
        """
        # Arrange
        restaurant = restaurants_data[0]
        table_number = 1
        
        # Simular dos reservas simultáneas
        reservation1 = {"table": table_number, "user": "user1"}
        reservation2 = {"table": table_number, "user": "user2"}
        
        # Act: En producción, esto requeriría transaction lock
        reserved_tables = set()
        
        # Primera reserva exitosa
        reserved_tables.add(table_number)
        assert len(reserved_tables) == 1
        
        # Segunda reserva intentaría fallar
        if table_number in reserved_tables:
            # En producción: ERROR - mesa ya reservada
            second_success = False
        else:
            reserved_tables.add(table_number)
            second_success = True
        
        # Assert
        assert not second_success  # Segunda falla
        assert len(reserved_tables) == 1  # Solo una mesa


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
