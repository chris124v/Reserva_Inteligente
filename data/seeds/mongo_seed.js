// MongoDB seed script for reserva_inteligente
// Run with: mongosh --file mongo_seed.js --host <mongos-host> --port 27017
// IMPORTANT: Run mongo_cleanup.js BEFORE this script to ensure clean state.
//
// NOTE: Users are managed in AWS Cognito and are not inserted by this script.
//
// ID mapping:
// usuario_id 1-5: References to Cognito users (not inserted here)
// restaurante_id: Auto-generated (1-7)
// menu_id: Auto-generated (1-28)
// reservation_id: Auto-generated (1-9)
// order_id: Auto-generated (1-12)
//

db = db.getSiblingDB('reserva_inteligente');

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

print('Mongo seed completed');
