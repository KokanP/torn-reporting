const db = require('../db');

// Helper to get profile by email
const getProfileByEmail = (email) => {
  return new Promise((resolve, reject) => {
    db.get('SELECT * FROM profiles WHERE email = ?', [email], (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });
};

// Google Auth mock login
exports.handleMockGoogleLogin = async (req, res) => {
  try {
    const { email, given_name, family_name } = req.body;
    if (!email) {
      return res.status(400).json({ error: 'Email is required' });
    }

    // Google returns email, given_name, family_name. Real names and emails are dead data
    // stored securely in database, but we assign a unique internal name
    const existing = await getProfileByEmail(email);
    let name;

    if (existing) {
      name = existing.name;
      db.run(
        'UPDATE profiles SET given_name = ?, family_name = ? WHERE email = ?',
        [given_name || '', family_name || '', email],
        (err) => {
          if (err) console.error('Failed to update profile real name', err);
        }
      );
    } else {
      name = `user_${Date.now()}`;
      db.run(
        'INSERT INTO profiles (name, email, given_name, family_name, nickname, last_nickname_change) VALUES (?, ?, ?, ?, NULL, NULL)',
        [name, email, given_name || '', family_name || ''],
        (err) => {
          if (err) console.error('Failed to insert new profile', err);
        }
      );
    }

    res.cookie('session_email', email, { httpOnly: true, path: '/' });
    return res.json({
      status: 'success',
      profile: {
        name,
        nickname: existing ? existing.nickname : null,
        profile_image: existing ? existing.profile_image : null,
        hero_image: existing ? existing.hero_image : null
      }
    });
  } catch (error) {
    console.error('Mock login error:', error);
    return res.status(500).json({ error: 'Internal Server Error' });
  }
};

// Get profile
exports.handleGetProfile = async (req, res) => {
  try {
    const email = req.cookies && req.cookies.session_email;
    if (!email) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const profile = await getProfileByEmail(email);
    if (!profile) {
      return res.status(404).json({ error: 'Profile not found' });
    }

    // Isolate real names and emails: do not return email, given_name, or family_name to frontend UI
    return res.json({
      name: profile.name,
      nickname: profile.nickname,
      last_nickname_change: profile.last_nickname_change,
      profile_image: profile.profile_image,
      hero_image: profile.hero_image
    });
  } catch (error) {
    console.error('Get profile error:', error);
    return res.status(500).json({ error: 'Internal Server Error' });
  }
};

// Update profile
exports.handleUpdateProfile = async (req, res) => {
  try {
    const email = req.cookies && req.cookies.session_email;
    if (!email) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { nickname } = req.body;
    if (!nickname || nickname.trim() === '') {
      return res.status(400).json({ error: 'Nickname is required' });
    }

    const profile = await getProfileByEmail(email);
    if (!profile) {
      return res.status(404).json({ error: 'Profile not found' });
    }

    const newNickname = nickname.trim();

    // Check uniqueness if nickname changed
    if (newNickname !== profile.nickname) {
      const isUnique = await new Promise((resolve) => {
        db.get('SELECT name FROM profiles WHERE nickname = ?', [newNickname], (err, row) => {
          if (row) resolve(false);
          else resolve(true);
        });
      });
      if (!isUnique) {
        return res.status(400).json({ error: 'Nickname is already taken' });
      }
    }

    const isOnboarding = !profile.nickname; // if nickname is null in DB, user is onboarding

    if (isOnboarding) {
      // Onboarding: allows the first nickname freely when last_nickname_change is NULL
      db.run(
        'UPDATE profiles SET nickname = ?, last_nickname_change = NULL WHERE email = ?',
        [newNickname, email],
        (err) => {
          if (err) {
            console.error('Update error:', err);
            return res.status(500).json({ error: 'Database update failed' });
          }
          return res.json({
            status: 'success',
            profile: {
              name: profile.name,
              nickname: newNickname,
              last_nickname_change: null,
              profile_image: profile.profile_image,
              hero_image: profile.hero_image
            }
          });
        }
      );
    } else {
      // Settings update: check 14-day limit
      if (profile.last_nickname_change) {
        const lastChange = new Date(profile.last_nickname_change);
        const now = new Date();
        const diffTime = Math.abs(now - lastChange);
        const diffDays = diffTime / (1000 * 60 * 60 * 24);
        if (diffDays < 14) {
          const remainingDays = Math.ceil(14 - diffDays);
          return res.status(429).json({
            error: `You must wait. Cooldown active. ${remainingDays} days remaining.`
          });
        }
      }

      // Either last_nickname_change is NULL (first change after onboarding) or cooldown passed (>14 days)
      const nowISO = new Date().toISOString();
      db.run(
        'UPDATE profiles SET nickname = ?, last_nickname_change = ? WHERE email = ?',
        [newNickname, nowISO, email],
        (err) => {
          if (err) {
            console.error('Update error:', err);
            return res.status(500).json({ error: 'Database update failed' });
          }
          return res.json({
            status: 'success',
            profile: {
              name: profile.name,
              nickname: newNickname,
              last_nickname_change: nowISO,
              profile_image: profile.profile_image,
              hero_image: profile.hero_image
            }
          });
        }
      );
    }
  } catch (error) {
    console.error('Update profile error:', error);
    return res.status(500).json({ error: 'Internal Server Error' });
  }
};
