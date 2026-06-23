// MongoDB seed script for reserva_inteligente
// Run with: mongosh --file mongo_seed.js --host <mongos-host> --port 27017
// IMPORTANT: Run mongo_cleanup.js BEFORE this script to ensure clean state.
//
// ID mapping (parte base, ids fijos):
// usuario_id 1-5: inserted below (must match Cognito users)
//   1=adminmongo (admin), 2=clientemongo (cliente), 3=admin2.mongo (admin),
//   4=lionel.mongo (cliente), 5=iniesta.mongo (cliente)
// restaurante_id 1-7 | menu_id 1-28 | reservation_id 1-9 | order_id 1-12
//
// Al final hay un bloque SINTETICO que agrega volumen para dashboards/analitica
// (mismos emails que Postgres y Cognito: admin{N}.seed@demo.com /
// cliente{N}.seed@demo.com). Es idempotente: se omite si ya hay > 5 usuarios.
// Totales tras el seed completo: ~39 usuarios (6 admin/33 cliente), 20
// restaurantes, 300 menus, ~150 reservas y ~200 pedidos en 6 meses (ene-jun 2026).
// Estados en minuscula (convencion Mongo): reservada/cancelada,
// entregado/cancelado/pendiente/..., domicilio/recogida/en_restaurante.
//

db = db.getSiblingDB('reserva_inteligente');

// Users (must be inserted first; admin_id=1 and admin_id=3 referenced by restaurants)
db.users.insertMany([
  {id:1, email:'adminmongo@gmail.com',      nombre:'Admin Mongo',        password_hash:'cognito', rol:'admin',   activo:true},
  {id:2, email:'clientemongo@gmail.com',    nombre:'Cliente Mongo',      password_hash:'cognito', rol:'cliente', activo:true},
  {id:3, email:'admin2.mongo@example.com',  nombre:'Zlatan Ibrahimovic', password_hash:'cognito', rol:'admin',   activo:true},
  {id:4, email:'lionel.mongo@example.com',  nombre:'Lionel Messi',       password_hash:'cognito', rol:'cliente', activo:true},
  {id:5, email:'iniesta.mongo@example.com', nombre:'Andres Iniesta',     password_hash:'cognito', rol:'cliente', activo:true}
]);
print('✓ Users inserted');

// Restaurants
db.restaurants.insertMany([
  {id:1, nombre: 'sapore tratoria', descripcion: 'Autentica comida italiana', direccion: 'Calle Roma 123', telefono: '555-0101', email: 'sapore@demo.com', admin_id:1, hora_apertura: '10:00', hora_cierre: '22:00', total_mesas:20},
  {id:2, nombre: 'villa italia', descripcion: 'Sabores de italia', direccion: 'Av Italia 45', telefono: '555-0102', email: 'villa@demo.com', admin_id:1, hora_apertura: '11:00', hora_cierre: '23:00', total_mesas:18},
  {id:3, nombre: 'los congos', descripcion: 'Cocina fusi\u00f3n', direccion: 'Calle Falsa 321', telefono: '555-0103', email: 'congos@demo.com', admin_id:1, hora_apertura: '12:00', hora_cierre: '22:30', total_mesas:15},
  {id:4, nombre: 'nacion sushi', descripcion: 'Sushi y mariscos', direccion: 'Muelle 8', telefono: '555-0104', email: 'sushi@demo.com', admin_id:1, hora_apertura: '12:00', hora_cierre: '23:00', total_mesas:12},
  {id:5, nombre: 'hamburguesas 360', descripcion: 'Hamburguesas gourmet', direccion: 'Boulevard 77', telefono: '555-0105', email: '360@demo.com', admin_id:1, hora_apertura: '10:00', hora_cierre: '23:00', total_mesas:25},
  {id:6, nombre: 'La Cancha Grill', descripcion: 'Parrilla tem\u00e1tica futbolera', direccion: 'Av Gol 9', telefono: '555-0201', email: 'cancha@demo.com', admin_id:3, hora_apertura: '12:00', hora_cierre: '23:00', total_mesas:16},
  {id:7, nombre: 'El Golazo Bistro', descripcion: 'Bistr\u00f3 y tapeo', direccion: 'Plaza Central 1', telefono: '555-0202', email: 'golazo@demo.com', admin_id:3, hora_apertura: '11:00', hora_cierre: '22:00', total_mesas:14}
]);

// Menus
const menus = [];
let id = 1;
const menuTemplates = [
  ['Pollo al Ajillo','Pollo tierno al ajillo',12.5,'principal'],
  ['Pasta Puttanesca','Pasta con salsa puttanesca',10.0,'pasta'],
  ['Filete de Res','Filete a la plancha',15.0,'carne'],
  ['Pizza Margherita','Pizza clÃ¡sica con tomate y albahaca',9.0,'pizza']
];
for (let r=1;r<=7;r++){
  for (let t=0;t<4;t++){
    const m = menuTemplates[t];
    menus.push({id: id, nombre: m[0], descripcion: m[1], precio: m[2], disponible: true, restaurante_id: r, tiempo_preparacion: 20 + t*5, categoria: m[3]});
    id++;
  }
}
db.menus.insertMany(menus);

// Reservations (3 per client: users 2,4,5)
db.reservations.insertMany([
  {id:1, usuario_id:2, restaurante_id:1, fecha: new Date('2026-05-10'), hora: '19:00', cantidad_personas:2, estado: 'reservada', notas:'Mesa cerca ventana'},
  {id:2, usuario_id:2, restaurante_id:3, fecha: new Date('2026-05-11'), hora: '20:00', cantidad_personas:4, estado:'reservada', notas:''},
  {id:3, usuario_id:2, restaurante_id:5, fecha: new Date('2026-05-12'), hora: '18:30', cantidad_personas:3, estado:'reservada', notas:'Cumplea\u00f1os'},
  {id:4, usuario_id:4, restaurante_id:2, fecha: new Date('2026-05-10'), hora: '19:30', cantidad_personas:2, estado:'reservada', notas:''},
  {id:5, usuario_id:4, restaurante_id:4, fecha: new Date('2026-05-11'), hora: '21:00', cantidad_personas:2, estado:'reservada', notas:''},
  {id:6, usuario_id:4, restaurante_id:6, fecha: new Date('2026-05-13'), hora: '20:00', cantidad_personas:3, estado:'reservada', notas:'Ventilaci\u00f3n preferida'},
  {id:7, usuario_id:5, restaurante_id:1, fecha: new Date('2026-05-14'), hora: '19:00', cantidad_personas:2, estado:'reservada', notas:''},
  {id:8, usuario_id:5, restaurante_id:7, fecha: new Date('2026-05-15'), hora: '20:30', cantidad_personas:4, estado:'reservada', notas:''},
  {id:9, usuario_id:5, restaurante_id:3, fecha: new Date('2026-05-16'), hora: '18:00', cantidad_personas:2, estado:'reservada', notas:'Cerca de la barra'}
]);

// Orders (4 per client)
db.orders.insertMany([
  {id:1, usuario_id:2, restaurante_id:1, items: [{menu_id:1,cantidad:1},{menu_id:4,cantidad:1}], subtotal:21.5, impuesto:1.72, total:23.22, estado:'entregado', tipo_entrega:'domicilio', direccion_entrega:'Calle Cliente 1', notas:''},
  {id:2, usuario_id:2, restaurante_id:3, items: [{menu_id:11,cantidad:2}], subtotal:28.0, impuesto:2.24, total:30.24, estado:'entregado', tipo_entrega:'recogida', direccion_entrega:null, notas:''},
  {id:3, usuario_id:2, restaurante_id:5, items: [{menu_id:17,cantidad:1},{menu_id:18,cantidad:1}], subtotal:13.0, impuesto:1.04, total:14.04, estado:'entregado', tipo_entrega:'domicilio', direccion_entrega:'Calle Cliente 1', notas:''},
  {id:4, usuario_id:2, restaurante_id:2, items: [{menu_id:6,cantidad:1}], subtotal:11.0, impuesto:0.88, total:11.88, estado:'entregado', tipo_entrega:'en_restaurante', direccion_entrega:null, notas:''},
  {id:5, usuario_id:4, restaurante_id:1, items: [{menu_id:2,cantidad:1}], subtotal:10.0, impuesto:0.8, total:10.8, estado:'entregado', tipo_entrega:'domicilio', direccion_entrega:'Calle Cliente 4', notas:''},
  {id:6, usuario_id:4, restaurante_id:4, items: [{menu_id:14,cantidad:2}], subtotal:24.0, impuesto:1.92, total:25.92, estado:'entregado', tipo_entrega:'recogida', direccion_entrega:null, notas:''},
  {id:7, usuario_id:4, restaurante_id:6, items: [{menu_id:22,cantidad:1}], subtotal:12.5, impuesto:1.0, total:13.5, estado:'entregado', tipo_entrega:'domicilio', direccion_entrega:'Calle Cliente 4', notas:''},
  {id:8, usuario_id:4, restaurante_id:7, items: [{menu_id:25,cantidad:1}], subtotal:16.5, impuesto:1.32, total:17.82, estado:'entregado', tipo_entrega:'en_restaurante', direccion_entrega:null, notas:''},
  {id:9, usuario_id:5, restaurante_id:2, items: [{menu_id:5,cantidad:1}], subtotal:13.0, impuesto:1.04, total:14.04, estado:'entregado', tipo_entrega:'domicilio', direccion_entrega:'Calle Cliente 5', notas:''},
  {id:10, usuario_id:5, restaurante_id:3, items: [{menu_id:12,cantidad:1},{menu_id:9,cantidad:1}], subtotal:22.5, impuesto:1.8, total:24.3, estado:'entregado', tipo_entrega:'recogida', direccion_entrega:null, notas:''},
  {id:11, usuario_id:5, restaurante_id:5, items: [{menu_id:19,cantidad:2}], subtotal:17.0, impuesto:1.36, total:18.36, estado:'entregado', tipo_entrega:'domicilio', direccion_entrega:'Calle Cliente 5', notas:''},
  {id:12, usuario_id:5, restaurante_id:7, items: [{menu_id:27,cantidad:1}], subtotal:17.0, impuesto:1.36, total:18.36, estado:'entregado', tipo_entrega:'en_restaurante', direccion_entrega:null, notas:''}
]);

print('Mongo seed base completed');

// ===========================================================================
// SEED EXTENDIDO (sintetico) para paridad con Postgres/Cognito
// Idempotente: se omite si ya hay > 5 usuarios.
// ===========================================================================
if (db.users.countDocuments() > 5) {
  print('Seed extendido Mongo omitido (ya hay > 5 usuarios).');
} else {
  const nombres = ['Carlos','Maria','Jose','Ana','Luis','Carmen','Juan','Laura','Pedro','Sofia','Diego','Valentina','Andres','Camila','Miguel','Daniela','Jorge','Gabriela','Fernando','Paula','Ricardo','Lucia','Sergio','Elena','Pablo','Marta','Hugo','Sara','Ivan','Noa'];
  const apellidos = ['Gomez','Rodriguez','Fernandez','Lopez','Martinez','Sanchez','Perez','Gonzalez','Ramirez','Torres','Flores','Rivera','Vargas','Castillo','Romero','Herrera','Medina','Aguilar','Reyes','Cruz'];
  const restNombres = ['Cafe del Parque','Mariscos La Bahia','Tacos El Rey','Burger Station','Sushi Zen','Pizza Forno','Asados Don Pepe','Wok Express','La Esquina Verde','Pasta & Vino','El Rincon Criollo','Mr. Pollo','Tapas Sur'];
  const zonas = ['Zona Norte','Zona Sur','Zona Centro','Zona Este','Zona Oeste','Centro Historico','Barrio Escalante','Sabana','Heredia Centro','Cartago Centro'];
  const platos = ['Especial de la Casa','Combo Familiar','Plato del Dia','Delicia','Clasico','Gourmet','Tradicional','Supremo','Ligero','Picante','Premium','Vegetariano','Infantil','Doble','Mixto'];
  const cats = ['principal','pasta','pizza','carne','pescado','sushi','entrada','acompanamiento','ensalada','postre','bebida'];
  const tipos = ['domicilio','recogida','en_restaurante'];
  function ri(n){ return Math.floor(Math.random()*n); }   // entero 0..n-1
  function round2(x){ return Math.round(x*100)/100; }

  // Usuarios: +4 admins (ids 6-9), +30 clientes (ids 10-39)
  const newUsers = [];
  let uid = 6;
  for (let g=1; g<=4; g++){
    newUsers.push({id: uid++, email:'admin'+g+'.seed@demo.com', nombre:'Admin Demo '+g, password_hash:'cognito', rol:'admin', activo:true});
  }
  for (let g=1; g<=30; g++){
    newUsers.push({id: uid++, email:'cliente'+g+'.seed@demo.com', nombre: nombres[g % nombres.length]+' '+apellidos[(g*3) % apellidos.length], password_hash:'cognito', rol:'cliente', activo:true});
  }
  db.users.insertMany(newUsers);

  const adminIds  = db.users.find({rol:'admin'}).toArray().map(function(u){ return u.id; });
  const clientIds = db.users.find({rol:'cliente'}).toArray().map(function(u){ return u.id; });

  // Restaurantes: +13 (ids 8-20), repartidos entre los admins
  const newRest = [];
  let rid = 8;
  for (let g=1; g<=13; g++){
    newRest.push({id: rid++, nombre: restNombres[g-1], descripcion:'Restaurante de seed para dashboards', direccion: zonas[g % zonas.length]+', Calle '+(10+g), telefono:'555-'+String(2000+g).padStart(4,'0'), email:'rest'+g+'.seed@demo.com', admin_id: adminIds[g % adminIds.length], hora_apertura:(8+(g%4))+':00', hora_cierre:(21+(g%3))+':00', total_mesas: 10+(g%20)});
  }
  db.restaurants.insertMany(newRest);

  // Menus: completar hasta 15 por restaurante (viejos y nuevos)
  let mid = db.menus.find().sort({id:-1}).limit(1).toArray()[0].id + 1;
  const newMenus = [];
  db.restaurants.find().sort({id:1}).toArray().forEach(function(rest){
    const existing = db.menus.countDocuments({restaurante_id: rest.id});
    for (let g=1; g <= 15-existing; g++){
      const idx = (existing+g) % platos.length;
      newMenus.push({id: mid++, nombre: platos[idx]+' '+(existing+g), descripcion:'Plato generado para seed', precio: round2(6+Math.random()*24), disponible:true, restaurante_id: rest.id, tiempo_preparacion: 10+ri(30), categoria: cats[(existing+g) % cats.length]});
    }
  });
  if (newMenus.length) db.menus.insertMany(newMenus);

  const start = new Date('2026-01-01').getTime();

  // Reservaciones: +141 en 6 meses, mezcla reservada/cancelada
  let resvId = db.reservations.find().sort({id:-1}).limit(1).toArray()[0].id + 1;
  const newResv = [];
  for (let i=0; i<141; i++){
    const d = new Date(start + ri(181)*86400000);
    const hora = (11+ri(10))+':'+['00','15','30','45'][ri(4)];
    newResv.push({id: resvId++, usuario_id: clientIds[ri(clientIds.length)], restaurante_id: 1+ri(20), fecha: d, hora: hora, cantidad_personas: 1+ri(8), estado: (Math.random()<0.2 ? 'cancelada' : 'reservada'), notas:''});
  }
  db.reservations.insertMany(newResv);

  // Pedidos: +188 en 6 meses, mezcla de estados, items reales del restaurante
  let ordId = db.orders.find().sort({id:-1}).limit(1).toArray()[0].id + 1;
  const menusByRest = {};
  db.menus.find().toArray().forEach(function(m){ (menusByRest[m.restaurante_id] = menusByRest[m.restaurante_id] || []).push(m); });
  const newOrders = [];
  for (let i=0; i<188; i++){
    const rest = 1+ri(20);
    const pool = menusByRest[rest] || [];
    const nItems = Math.min(1+ri(3), pool.length);
    const shuffled = pool.slice().sort(function(){ return Math.random()-0.5; }).slice(0, nItems);
    const items = []; let subtotal = 0;
    shuffled.forEach(function(m){ const c = 1+ri(3); items.push({menu_id: m.id, cantidad: c}); subtotal += m.precio*c; });
    subtotal = round2(subtotal);
    const impuesto = round2(subtotal*0.08);
    const total = round2(subtotal+impuesto);
    const r = Math.random();
    let estado;
    if (r<0.60) estado='entregado'; else if (r<0.75) estado='cancelado'; else if (r<0.85) estado='pendiente'; else if (r<0.92) estado='confirmado'; else if (r<0.97) estado='en_preparacion'; else estado='listo';
    const tipo = tipos[ri(3)];
    const client = clientIds[ri(clientIds.length)];
    const fecha = new Date(start + ri(181)*86400000 + (10+ri(13))*3600000);
    newOrders.push({id: ordId++, usuario_id: client, restaurante_id: rest, items: items, subtotal: subtotal, impuesto: impuesto, total: total, estado: estado, tipo_entrega: tipo, direccion_entrega: (tipo==='domicilio' ? 'Calle Cliente '+client : null), notas:'', fecha_creacion: fecha});
  }
  db.orders.insertMany(newOrders);

  print('Seed extendido Mongo aplicado: usuarios='+db.users.countDocuments()+', restaurantes='+db.restaurants.countDocuments()+', menus='+db.menus.countDocuments()+', reservas='+db.reservations.countDocuments()+', pedidos='+db.orders.countDocuments());
}
print('Mongo seed completed');
