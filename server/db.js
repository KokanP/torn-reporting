const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const dbPath = path.resolve(__dirname, 'database.sqlite');

const db = new sqlite3.Database(dbPath, (err) => {
  if (err) {
    console.error('Could not connect to database', err);
  } else {
    console.log('Connected to SQLite database');
  }
});

db.serialize(() => {
  db.run(`
    CREATE TABLE IF NOT EXISTS profiles (
      name TEXT PRIMARY KEY,
      email TEXT UNIQUE,
      given_name TEXT,
      family_name TEXT,
      nickname TEXT UNIQUE,
      last_nickname_change TEXT DEFAULT NULL,
      profile_image TEXT,
      hero_image TEXT
    )
  `);
});

module.exports = db;
