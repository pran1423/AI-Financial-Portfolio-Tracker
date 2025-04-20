// backend/server.js
require('dotenv').config();

const path = require('path');
const express = require('express');
const cors = require('cors');

// connect to your DB
require('../database/db');

const authRoutes           = require('./routes/auth');
const userRoutes           = require('./routes/user');
const sentimentRoutes      = require('./routes/sentiment');
const predictionsRoutes    = require('./routes/predictions');
const chartRoutes          = require('./routes/chart');
const recommendationsRoutes= require('./routes/recommendations');
const tickersRoutes        = require('./routes/tickers');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());

app.use(express.json());

// Serve everything in frontend
app.use(express.static(path.join(__dirname, '../frontend')));

app.use('/api/auth', authRoutes);
app.use('/api/user', userRoutes);
app.use('/api/sentiment', sentimentRoutes);
app.use('/api/predictions', predictionsRoutes);
app.use('/api/chart', chartRoutes);
app.use('/api/recommendations',recommendationsRoutes);
app.use('/api/tickers',tickersRoutes);

// For the root URL, send your landing page
app.get('/', (req, res) => {
  res.sendFile(
    path.join(__dirname, '../frontend/landing-page/landingPage.html')
  );
});

app.get('*', (req, res, next) => {
  if (req.path.startsWith('/api/')) {

    return next();
  }
  res.sendFile(
    path.join(__dirname, '../frontend/landing-page/landingPage.html')
  );
});

// Start the server
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
});
