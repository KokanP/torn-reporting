const db = require('./db');

db.serialize(() => {
  // Check if columns exist by trying to add them
  db.run("ALTER TABLE profiles ADD COLUMN last_nickname_change TEXT DEFAULT NULL", (err) => {
    if (err) {
      console.log("last_nickname_change column already exists or table not created yet");
    } else {
      console.log("Added column last_nickname_change to profiles");
    }
  });

  db.run("ALTER TABLE profiles ADD COLUMN profile_image TEXT", (err) => {
    if (err) {
      console.log("profile_image column already exists or table not created yet");
    } else {
      console.log("Added column profile_image to profiles");
    }
  });

  db.run("ALTER TABLE profiles ADD COLUMN hero_image TEXT", (err) => {
    if (err) {
      console.log("hero_image column already exists or table not created yet");
    } else {
      console.log("Added column hero_image to profiles");
    }
  });
});
