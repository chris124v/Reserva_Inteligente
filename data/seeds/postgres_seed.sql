-- Seed data for Postgres (restaurantes_db)
-- IMPORTANT: Run postgres_cleanup.sql BEFORE this script to ensure clean state.
--
-- Este seed tiene dos partes:
--   1) Datos base explicitos (ids 1..N) que NO cambian: los 5 usuarios ligados a
--      Cognito, 7 restaurantes, 28 menus, 9 reservas y 12 pedidos originales.
--   2) Un bloque PL/pgSQL al final que genera datos sinteticos adicionales para
--      poblar los dashboards de Metabase y los analisis de Spark con volumen y
--      variedad (varios meses, estados mezclados, mas zonas). Es idempotente:
--      solo corre si aun no se ha aplicado (detecta < 30 clientes).
--
-- Totales tras aplicar el seed completo:
--   usuarios:      ~39  (6 admins, 33 clientes)
--   restaurantes:  20
--   menus:         300  (15 por restaurante)
--   reservaciones: ~150 repartidas en 6 meses (ene-jun 2026), reservada/cancelada
--   pedidos:       ~200 repartidos en 6 meses, mezcla de estados y tipos de entrega
--
-- NOTA Cognito: los usuarios sinteticos usan password_hash 'cognito' como
-- placeholder igual que los base, pero NO existen en el pool de Cognito, asi que
-- son solo datos para analitica/dashboards; no pueden autenticarse via la API.
--
-- ID mapping (parte base, ids fijos):
-- usuario_id 1-5: inserted below (must match Cognito users)
--   1=adminpostgres (admin), 2=clientepostgres (cliente), 3=admin2.postgres (admin),
--   4=lionel.postgres (cliente), 5=iniesta.postgres (cliente)
-- restaurante_id: 1-7   | menu_id: 1-28 | reservation_id: 1-9 | order_id: 1-12
-- Los ids >= esos rangos los asignan las secuencias en el bloque PL/pgSQL final.

-- Users (must be inserted first; admin_id=1 and admin_id=3 referenced by restaurants)
INSERT INTO users (id, email, nombre, password_hash, rol, activo, fecha_creacion, fecha_actualizacion) VALUES
(1, 'adminpostgres@gmail.com',   'Admin Postgres',    'cognito', 'ADMIN',   true, NOW(), NOW()),
(2, 'clientepostgres@gmail.com', 'Cliente Postgres',  'cognito', 'CLIENTE', true, NOW(), NOW()),
(3, 'admin2.postgres@gmail.com', 'Cristiano Ronaldo', 'cognito', 'ADMIN',   true, NOW(), NOW()),
(4, 'lionel.postgres@gmail.com', 'Lionel Messi',      'cognito', 'CLIENTE', true, NOW(), NOW()),
(5, 'iniesta.postgres@gmail.com','Andres Iniesta',    'cognito', 'CLIENTE', true, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

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

-- ===========================================================================
-- SEED EXTENDIDO (sintetico) para poblar dashboards Metabase + analisis Spark
-- ---------------------------------------------------------------------------
-- Idempotente: el bloque entero se omite si ya hay >= 30 clientes.
-- Genera, sobre los datos base de arriba:
--   +4 admins, +30 clientes, +13 restaurantes, menus hasta 15 por restaurante,
--   +141 reservaciones y +188 pedidos, repartidos en 6 meses (ene-jun 2026)
--   con mezcla realista de estados, categorias, zonas y tipos de entrega.
-- Los valores de columnas enum por fila se insertan via format('%L', ...) para
-- que Postgres los auto-convierta al tipo enum destino sin depender del nombre
-- exacto del tipo (creado por SQLAlchemy, no por una migracion explicita).
-- ===========================================================================
DO $$
DECLARE
    v_admin_ids  int[];
    v_client_ids int[];
    v_nombres    text[] := ARRAY['Carlos','Maria','Jose','Ana','Luis','Carmen','Juan','Laura',
                                 'Pedro','Sofia','Diego','Valentina','Andres','Camila','Miguel',
                                 'Daniela','Jorge','Gabriela','Fernando','Paula','Ricardo','Lucia',
                                 'Sergio','Elena','Pablo','Marta','Hugo','Sara','Ivan','Noa'];
    v_apellidos  text[] := ARRAY['Gomez','Rodriguez','Fernandez','Lopez','Martinez','Sanchez',
                                 'Perez','Gonzalez','Ramirez','Torres','Flores','Rivera','Vargas',
                                 'Castillo','Romero','Herrera','Medina','Aguilar','Reyes','Cruz'];
    v_rest_nombres text[] := ARRAY['Cafe del Parque','Mariscos La Bahia','Tacos El Rey',
                                   'Burger Station','Sushi Zen','Pizza Forno','Asados Don Pepe',
                                   'Wok Express','La Esquina Verde','Pasta & Vino',
                                   'El Rincon Criollo','Mr. Pollo','Tapas Sur'];
    v_zonas      text[] := ARRAY['Zona Norte','Zona Sur','Zona Centro','Zona Este','Zona Oeste',
                                 'Centro Historico','Barrio Escalante','Sabana','Heredia Centro',
                                 'Cartago Centro'];
    v_platos     text[] := ARRAY['Especial de la Casa','Combo Familiar','Plato del Dia','Delicia',
                                 'Clasico','Gourmet','Tradicional','Supremo','Ligero','Picante',
                                 'Premium','Vegetariano','Infantil','Doble','Mixto'];
    v_cats       text[] := ARRAY['principal','pasta','pizza','carne','pescado','sushi','entrada',
                                 'acompanamiento','ensalada','postre','bebida'];
    r          RECORD;
    v_existing int;
    v_to_add   int;
    i          int;
    v_rest     int;
    v_client   int;
    v_nitems   int;
    v_items    json;
    v_subtotal numeric;
    v_impuesto numeric;
    v_total    numeric;
    v_estado   text;
    v_tipo     text;
    v_dir      text;
    v_fecha    timestamp;
    v_rnd      double precision;
BEGIN
    IF (SELECT COUNT(*) FROM users WHERE rol = 'CLIENTE') >= 30 THEN
        RAISE NOTICE 'Seed extendido ya aplicado (>= 30 clientes); se omite.';
        RETURN;
    END IF;

    -- Los INSERT explicitos con id arriba NO avanzan las secuencias; las fijamos
    -- al maximo actual para que los inserts por secuencia no choquen con esos ids.
    PERFORM setval(pg_get_serial_sequence('users','id'),        (SELECT MAX(id) FROM users));
    PERFORM setval(pg_get_serial_sequence('restaurants','id'),  (SELECT MAX(id) FROM restaurants));
    PERFORM setval(pg_get_serial_sequence('menus','id'),        (SELECT MAX(id) FROM menus));
    PERFORM setval(pg_get_serial_sequence('reservations','id'), (SELECT MAX(id) FROM reservations));
    PERFORM setval(pg_get_serial_sequence('orders','id'),       (SELECT MAX(id) FROM orders));

    -- ---- Usuarios: +4 admins (total 6) -------------------------------------
    INSERT INTO users (email, nombre, password_hash, rol, activo, fecha_creacion, fecha_actualizacion)
    SELECT 'admin' || g || '.seed@demo.com',
           'Admin Demo ' || g,
           'cognito', 'ADMIN', true, NOW(), NOW()
    FROM generate_series(1, 4) g;

    -- ---- Usuarios: +30 clientes (total 33) ---------------------------------
    INSERT INTO users (email, nombre, password_hash, rol, activo, fecha_creacion, fecha_actualizacion)
    SELECT 'cliente' || g || '.seed@demo.com',
           v_nombres[1 + (g % array_length(v_nombres, 1))] || ' ' ||
           v_apellidos[1 + ((g * 3) % array_length(v_apellidos, 1))],
           'cognito', 'CLIENTE', true, NOW(), NOW()
    FROM generate_series(1, 30) g;

    SELECT array_agg(id) INTO v_admin_ids  FROM users WHERE rol = 'ADMIN';
    SELECT array_agg(id) INTO v_client_ids FROM users WHERE rol = 'CLIENTE';

    -- ---- Restaurantes: +13 (total 20), repartidos entre los admins ---------
    INSERT INTO restaurants (nombre, descripcion, direccion, telefono, email, admin_id,
                             hora_apertura, hora_cierre, total_mesas, fecha_creacion, fecha_actualizacion)
    SELECT v_rest_nombres[g],
           'Restaurante de seed para dashboards',
           v_zonas[1 + (g % array_length(v_zonas, 1))] || ', Calle ' || (10 + g),
           '555-' || lpad((2000 + g)::text, 4, '0'),
           'rest' || g || '.seed@demo.com',
           v_admin_ids[1 + (g % array_length(v_admin_ids, 1))],
           make_time(8 + (g % 4), 0, 0),
           make_time(21 + (g % 3), 0, 0),
           10 + (g % 20),
           NOW(), NOW()
    FROM generate_series(1, 13) g;

    -- ---- Menus: completar hasta 15 por restaurante (viejos y nuevos) -------
    FOR r IN SELECT id FROM restaurants ORDER BY id LOOP
        v_existing := (SELECT COUNT(*) FROM menus WHERE restaurante_id = r.id);
        v_to_add   := 15 - v_existing;
        IF v_to_add > 0 THEN
            INSERT INTO menus (nombre, descripcion, precio, disponible, restaurante_id,
                               tiempo_preparacion, categoria, fecha_creacion, fecha_actualizacion)
            SELECT v_platos[1 + ((v_existing + g) % array_length(v_platos, 1))] || ' ' || (v_existing + g),
                   'Plato generado para seed',
                   round((6 + random() * 24)::numeric, 2),
                   true,
                   r.id,
                   10 + (random() * 30)::int,
                   v_cats[1 + ((v_existing + g) % array_length(v_cats, 1))],
                   NOW(), NOW()
            FROM generate_series(1, v_to_add) g;
        END IF;
    END LOOP;

    -- ---- Reservaciones: +141 (total ~150) en 6 meses ----------------------
    FOR i IN 1..141 LOOP
        v_client := v_client_ids[1 + floor(random() * array_length(v_client_ids, 1))::int];
        v_rest   := 1 + floor(random() * 20)::int;
        v_estado := CASE WHEN random() < 0.2 THEN 'cancelada' ELSE 'reservada' END;
        EXECUTE format(
            'INSERT INTO reservations (usuario_id, restaurante_id, fecha, hora, cantidad_personas,
                                       estado, notas, fecha_creacion, fecha_actualizacion)
             VALUES (%s, %s, %L, %L, %s, %L, NULL, NOW(), NOW())',
            v_client,
            v_rest,
            (DATE '2026-01-01' + (floor(random() * 181))::int)::text,
            make_time(11 + floor(random() * 10)::int, (ARRAY[0,15,30,45])[1 + floor(random() * 4)::int], 0)::text,
            1 + floor(random() * 8)::int,
            v_estado
        );
    END LOOP;

    -- ---- Pedidos: +188 (total ~200) en 6 meses ----------------------------
    FOR i IN 1..188 LOOP
        v_rest   := 1 + floor(random() * 20)::int;
        v_client := v_client_ids[1 + floor(random() * array_length(v_client_ids, 1))::int];
        v_nitems := 1 + floor(random() * 3)::int;   -- 1..3 items por pedido

        SELECT json_agg(json_build_object('menu_id', sub.id, 'cantidad', sub.cantidad)),
               COALESCE(SUM(sub.precio * sub.cantidad), 0)
        INTO v_items, v_subtotal
        FROM (
            SELECT id, precio, (1 + floor(random() * 3)::int) AS cantidad
            FROM menus
            WHERE restaurante_id = v_rest AND disponible = true
            ORDER BY random()
            LIMIT v_nitems
        ) sub;

        v_subtotal := round(v_subtotal, 2);
        v_impuesto := round(v_subtotal * 0.08, 2);
        v_total    := round(v_subtotal + v_impuesto, 2);

        v_rnd := random();
        v_estado := CASE
            WHEN v_rnd < 0.60 THEN 'ENTREGADO'
            WHEN v_rnd < 0.75 THEN 'CANCELADO'
            WHEN v_rnd < 0.85 THEN 'PENDIENTE'
            WHEN v_rnd < 0.92 THEN 'CONFIRMADO'
            WHEN v_rnd < 0.97 THEN 'EN_PREPARACION'
            ELSE 'LISTO'
        END;
        v_tipo := (ARRAY['DOMICILIO','RECOGIDA','EN_RESTAURANTE'])[1 + floor(random() * 3)::int];
        v_dir  := CASE WHEN v_tipo = 'DOMICILIO' THEN 'Calle Cliente ' || v_client ELSE NULL END;
        v_fecha := TIMESTAMP '2026-01-01 00:00:00'
                   + make_interval(days  => floor(random() * 181)::int,
                                   hours => (10 + floor(random() * 13))::int,
                                   mins  => floor(random() * 60)::int);

        EXECUTE format(
            'INSERT INTO orders (usuario_id, restaurante_id, items, subtotal, impuesto, total,
                                 estado, tipo_entrega, direccion_entrega, notas,
                                 fecha_creacion, fecha_actualizacion)
             VALUES (%s, %s, %L, %s, %s, %s, %L, %L, %L, %L, %L, %L)',
            v_client, v_rest, v_items::text, v_subtotal, v_impuesto, v_total,
            v_estado, v_tipo, v_dir, '', v_fecha::text, v_fecha::text
        );
    END LOOP;

    RAISE NOTICE 'Seed extendido aplicado: % admins, % clientes, % restaurantes, % menus, % reservas, % pedidos.',
        (SELECT COUNT(*) FROM users WHERE rol = 'ADMIN'),
        (SELECT COUNT(*) FROM users WHERE rol = 'CLIENTE'),
        (SELECT COUNT(*) FROM restaurants),
        (SELECT COUNT(*) FROM menus),
        (SELECT COUNT(*) FROM reservations),
        (SELECT COUNT(*) FROM orders);
END $$;
