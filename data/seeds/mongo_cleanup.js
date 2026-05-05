// MongoDB cleanup script for reserva_inteligente
// Run BEFORE loading mongo_seed.js with: mongosh --file mongo_cleanup.js

db = db.getSiblingDB('reserva_inteligente');

// Drop all collections
try {
  db.orders.drop();
  print('✓ Dropped orders collection');
} catch(e) {
  print('  orders collection not found or error: ' + e.message);
}

try {
  db.reservations.drop();
  print('✓ Dropped reservations collection');
} catch(e) {
  print('  reservations collection not found or error: ' + e.message);
}

try {
  db.menus.drop();
  print('✓ Dropped menus collection');
} catch(e) {
  print('  menus collection not found or error: ' + e.message);
}

try {
  db.restaurants.drop();
  print('✓ Dropped restaurants collection');
} catch(e) {
  print('  restaurants collection not found or error: ' + e.message);
}

try {
  db.users.drop();
  print('✓ Dropped users collection');
} catch(e) {
  print('  users collection not found or error: ' + e.message);
}

// Verify cleanup
print('\nCleanup complete. Current collections:');
db.getCollectionNames().forEach(function(name) {
  print('- ' + name + ': ' + db[name].countDocuments() + ' documents');
});
