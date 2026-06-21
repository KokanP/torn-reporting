const express = require('express');
const cors = require('cors');
const axios = require('axios');
const profileController = require('./controllers/profileController');

const app = express();
const PORT = 8080;

app.use(cors({
  origin: true,
  credentials: true
}));

app.use(express.json());

// Custom cookie parser middleware
app.use((req, res, next) => {
  const cookies = {};
  const cookieHeader = req.headers.cookie;
  if (cookieHeader) {
    cookieHeader.split(';').forEach((cookie) => {
      const parts = cookie.split('=');
      cookies[parts.shift().trim()] = decodeURIComponent(parts.join('='));
    });
  }
  req.cookies = cookies;
  next();
});

// Auth & profile routes
app.post('/api/auth/google/mock', profileController.handleMockGoogleLogin);
app.get('/api/profile', profileController.handleGetProfile);
app.post('/api/profile/update', profileController.handleUpdateProfile);

// Forward calculations to Python FastAPI on port 8081
app.post('/api/generate', async (req, res) => {
  try {
    const response = await axios.post('http://localhost:8081/api/generate', req.body);
    res.json(response.data);
  } catch (err) {
    console.error('FastAPI calculation proxy error:', err.message);
    res.status(err.response?.status || 500).json(err.response?.data || { error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Express auth and profile server running on http://localhost:${PORT}`);
});
