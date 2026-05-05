-- Minimal seed data for Postgres (restaurantes_db)
-- NOTE: Users are managed in AWS Cognito and are not inserted by this script.
-- IMPORTANT: Run postgres_cleanup.sql BEFORE this script to ensure clean state.
--
-- ID mapping:
-- usuario_id 1-5: References to Cognito users (not inserted here)
-- restaurante_id: Auto-generated (1-7)
-- menu_id: Auto-generated (1-28)
-- reservation_id: Auto-generated (1-9)
-- order_id: Auto-generated (1-12)
--
-- Restaurants (5 owned by base admin id=1, 2 owned by admin id=3)
INSERT INTO restaurants (id, nombre, descripcion, direccion, telefono, email, admin_id, hora_apertura, hora_cierre, total_mesas, fecha_creacion, fecha_actualizacion) VALUES
(1, 'sapore tratoria', 'Autentica comida italiana', 'Calle Roma 123', '555-0101', 'sapore@demo.com', 1, '10:00', '22:00', 20, NOW(), NOW()),
(2, 'villa italia', 'Sabores de italia', 'Av Italia 45', '555-0102', 'villa@demo.com', 1, '11:00', '23:00', 18, NOW(), NOW()),
(3, 'los congos', 'Cocina fusiÃ³n', 'Calle Falsa 321', '555-0103', 'congos@demo.com', 1, '12:00', '22:30', 15, NOW(), NOW()),
(4, 'nacion sushi', 'Sushi y mariscos', 'Muelle 8', '555-0104', 'sushi@demo.com', 1, '12:00', '23:00', 12, NOW(), NOW()),
(5, 'hamburguesas 360', 'Hamburguesas gourmet', 'Boulevard 77', '555-0105', '360@demo.com', 1, '10:00', '23:00', 25, NOW(), NOW()),
(6, 'La Cancha Grill', 'Parrilla temÃ¡tica futbolera', 'Av Gol 9', '555-0201', 'cancha@demo.com', 3, '12:00', '23:00', 16, NOW(), NOW()),
(7, 'El Golazo Bistro', 'BistrÃ³ y tapeo', 'Plaza Central 1', '555-0202', 'golazo@demo.com', 3, '11:00', '22:00', 14, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
  nombre = EXCLUDED.nombre,
  descripcion = EXCLUDED.descripcion,
  direccion = EXCLUDED.direccion,
  telefono = EXCLUDED.telefono,
  email = EXCLUDED.email,
  admin_id = EXCLUDED.admin_id,
  hora_apertura = EXCLUDED.hora_apertura,
  hora_cierre = EXCLUDED.hora_cierre,
  total_mesas = EXCLUDED.total_mesas,
  fecha_actualizacion = EXCLUDED.fecha_actualizacion;

-- Menus (4 per restaurant) -> ids 1..28
INSERT INTO menus (id, nombre, descripcion, precio, disponible, restaurante_id, tiempo_preparacion, categoria, fecha_creacion, fecha_actualizacion) VALUES
-- Restaurant 1
(1, 'Pollo al Ajillo', 'Pollo tierno al ajillo', 12.5, true, 1, 25, 'principal', NOW(), NOW()),
(2, 'Pasta Puttanesca', 'Pasta con salsa puttanesca', 10.0, true, 1, 20, 'pasta', NOW(), NOW()),
(3, 'Filete de Res', 'Filete a la plancha', 15.0, true, 1, 30, 'carne', NOW(), NOW()),
(4, 'Pizza Margherita', 'Pizza clÃ¡sica con tomate y albahaca', 9.0, true, 1, 18, 'pizza', NOW(), NOW()),
-- Restaurant 2
(5, 'Pollo Parmesano', 'Pollo con salsa de tomate y parmesano', 13.0, true, 2, 25, 'principal', NOW(), NOW()),
(6, 'Pasta Carbonara', 'Pasta con salsa carbonara', 11.0, true, 2, 20, 'pasta', NOW(), NOW()),
(7, 'SalmÃ³n al Horno', 'SalmÃ³n con hierbas', 16.0, true, 2, 28, 'pescado', NOW(), NOW()),
(8, 'Pizza Quattro Formaggi', 'Pizza 4 quesos', 11.5, true, 2, 18, 'pizza', NOW(), NOW()),
-- Restaurant 3
(9, 'Pollo Picante', 'Pollo en salsa picante', 12.0, true, 3, 22, 'principal', NOW(), NOW()),
(10, 'Ravioli de Carne', 'Ravioli relleno de carne', 11.5, true, 3, 25, 'pasta', NOW(), NOW()),
(11, 'Lomo Saltado', 'Plato de carne estilo sudamericano', 14.0, true, 3, 30, 'carne', NOW(), NOW()),
(12, 'Pizza Pepperoni', 'Pizza con pepperoni', 10.5, true, 3, 18, 'pizza', NOW(), NOW()),
-- Restaurant 4
(13, 'Pollo Teriyaki', 'Pollo con salsa teriyaki', 13.5, true, 4, 22, 'principal', NOW(), NOW()),
(14, 'Uramaki Especial', 'Rollos variados', 12.0, true, 4, 25, 'sushi', NOW(), NOW()),
(15, 'SalmÃ³n Nigiri', 'Nigiri de salmÃ³n fresco', 9.5, true, 4, 10, 'sushi', NOW(), NOW()),
(16, 'Tempura Vegetal', 'Tempura de verduras', 8.0, true, 4, 18, 'entrada', NOW(), NOW()),
-- Restaurant 5
(17, 'Hamburguesa ClÃ¡sica', 'Carne, lechuga, tomate, queso', 9.0, true, 5, 15, 'principal', NOW(), NOW()),
(18, 'Papas Fritas', 'Papas crocantes', 4.0, true, 5, 10, 'acompanamiento', NOW(), NOW()),
(19, 'Pollo Crispy', 'Tiras de pollo crujiente', 8.5, true, 5, 15, 'principal', NOW(), NOW()),
(20, 'Pizza BBQ', 'Pizza con pollo BBQ', 11.0, true, 5, 20, 'pizza', NOW(), NOW()),
-- Restaurant 6
(21, 'Parrilla Mixta', 'Variedad de carnes a la parrilla', 18.0, true, 6, 35, 'carne', NOW(), NOW()),
(22, 'Pollo a la Brasa', 'Pollo asado con especias', 12.5, true, 6, 30, 'principal', NOW(), NOW()),
(23, 'Pasta al Pesto', 'Pasta con pesto fresco', 10.0, true, 6, 20, 'pasta', NOW(), NOW()),
(24, 'Ensalada Gol', 'Ensalada fresca', 7.0, true, 6, 10, 'ensalada', NOW(), NOW()),
-- Restaurant 7
(25, 'Bistec al Chimichurri', 'Bistec con chimichurri', 16.5, true, 7, 30, 'carne', NOW(), NOW()),
(26, 'Pizza Especial', 'Pizza con ingredientes premium', 13.0, true, 7, 20, 'pizza', NOW(), NOW()),
(27, 'SalmÃ³n a la Plancha', 'SalmÃ³n con guarniciÃ³n', 17.0, true, 7, 28, 'pescado', NOW(), NOW()),
(28, 'Pasta Alfredo', 'Pasta con salsa alfredo', 11.0, true, 7, 22, 'pasta', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
  nombre = EXCLUDED.nombre,
  descripcion = EXCLUDED.descripcion,
  precio = EXCLUDED.precio,
  disponible = EXCLUDED.disponible,
  restaurante_id = EXCLUDED.restaurante_id,
  tiempo_preparacion = EXCLUDED.tiempo_preparacion,
  categoria = EXCLUDED.categoria,
  fecha_actualizacion = EXCLUDED.fecha_actualizacion;
-- Reservations: 3 per client (clients: 2,4,5)
INSERT INTO reservations (id, usuario_id, restaurante_id, fecha, hora, cantidad_personas, estado, notas, fecha_creacion, fecha_actualizacion) VALUES
(1, 2, 1, '2026-05-10', '19:00', 2, 'reservada', 'Mesa cerca ventana', NOW(), NOW()),
(2, 2, 3, '2026-05-11', '20:00', 4, 'reservada', '', NOW(), NOW()),
(3, 2, 5, '2026-05-12', '18:30', 3, 'reservada', 'Cumplea\u00f1os', NOW(), NOW()),
(4, 4, 2, '2026-05-10', '19:30', 2, 'reservada', '', NOW(), NOW()),
(5, 4, 4, '2026-05-11', '21:00', 2, 'reservada', '', NOW(), NOW()),
(6, 4, 6, '2026-05-13', '20:00', 3, 'reservada', 'Ventilaci\u00f3n preferida', NOW(), NOW()),
(7, 5, 1, '2026-05-14', '19:00', 2, 'reservada', '', NOW(), NOW()),
(8, 5, 7, '2026-05-15', '20:30', 4, 'reservada', '', NOW(), NOW()),
(9, 5, 3, '2026-05-16', '18:00', 2, 'reservada', 'Cerca de la barra', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
  usuario_id = EXCLUDED.usuario_id,
  restaurante_id = EXCLUDED.restaurante_id,
  fecha = EXCLUDED.fecha,
  hora = EXCLUDED.hora,
  cantidad_personas = EXCLUDED.cantidad_personas,
  estado = EXCLUDED.estado,
  notas = EXCLUDED.notas,
  fecha_actualizacion = EXCLUDED.fecha_actualizacion;

-- Orders: 4 per client, items use menu ids
INSERT INTO orders (id, usuario_id, restaurante_id, items, subtotal, impuesto, total, estado, tipo_entrega, direccion_entrega, notas, fecha_creacion, fecha_actualizacion) VALUES
(1, 2, 1, '[{"menu_id":1,"cantidad":1},{"menu_id":4,"cantidad":1}]', 21.5, 1.72, 23.22, 'ENTREGADO', 'DOMICILIO', 'Calle Cliente 1', '', NOW(), NOW()),
(2, 2, 3, '[{"menu_id":11,"cantidad":2}]', 28.0, 2.24, 30.24, 'ENTREGADO', 'RECOGIDA', NULL, '', NOW(), NOW()),
(3, 2, 5, '[{"menu_id":17,"cantidad":1},{"menu_id":18,"cantidad":1}]', 13.0, 1.04, 14.04, 'ENTREGADO', 'DOMICILIO', 'Calle Cliente 1', '', NOW(), NOW()),
(4, 2, 2, '[{"menu_id":6,"cantidad":1}]', 11.0, 0.88, 11.88, 'ENTREGADO', 'EN_RESTAURANTE', NULL, '', NOW(), NOW()),
(5, 4, 1, '[{"menu_id":2,"cantidad":1}]', 10.0, 0.8, 10.8, 'ENTREGADO', 'DOMICILIO', 'Calle Cliente 4', '', NOW(), NOW()),
(6, 4, 4, '[{"menu_id":14,"cantidad":2}]', 24.0, 1.92, 25.92, 'ENTREGADO', 'RECOGIDA', NULL, '', NOW(), NOW()),
(7, 4, 6, '[{"menu_id":22,"cantidad":1}]', 12.5, 1.0, 13.5, 'ENTREGADO', 'DOMICILIO', 'Calle Cliente 4', '', NOW(), NOW()),
(8, 4, 7, '[{"menu_id":25,"cantidad":1}]', 16.5, 1.32, 17.82, 'ENTREGADO', 'EN_RESTAURANTE', NULL, '', NOW(), NOW()),
(9, 5, 2, '[{"menu_id":5,"cantidad":1}]', 13.0, 1.04, 14.04, 'ENTREGADO', 'DOMICILIO', 'Calle Cliente 5', '', NOW(), NOW()),
(10, 5, 3, '[{"menu_id":12,"cantidad":1},{"menu_id":9,"cantidad":1}]', 22.5, 1.8, 24.3, 'ENTREGADO', 'RECOGIDA', NULL, '', NOW(), NOW()),
(11, 5, 5, '[{"menu_id":19,"cantidad":2}]', 17.0, 1.36, 18.36, 'ENTREGADO', 'DOMICILIO', 'Calle Cliente 5', '', NOW(), NOW()),
(12, 5, 7, '[{"menu_id":27,"cantidad":1}]', 17.0, 1.36, 18.36, 'ENTREGADO', 'EN_RESTAURANTE', NULL, '', NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
  usuario_id = EXCLUDED.usuario_id,
  restaurante_id = EXCLUDED.restaurante_id,
  items = EXCLUDED.items,
  subtotal = EXCLUDED.subtotal,
  impuesto = EXCLUDED.impuesto,
  total = EXCLUDED.total,
  estado = EXCLUDED.estado,
  tipo_entrega = EXCLUDED.tipo_entrega,
  direccion_entrega = EXCLUDED.direccion_entrega,
  notas = EXCLUDED.notas,
  fecha_actualizacion = EXCLUDED.fecha_actualizacion;
