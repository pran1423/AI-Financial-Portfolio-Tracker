
require('dotenv').config();

const path = require('path');
const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');

// Load the database connection
require('../database/db');

// Import route files
const authRoutes = require('./routes/auth');
const userRoutes = require('./routes/user');
const sentimentRoutes = require('./routes/sentiment');
const predictionsRoutes = require('./routes/predictions');
const chartRoutes = require('./routes/chart');
const recommendationsRoutes = require('./routes/recommendations');
const tickersRoutes     = require('./routes/tickers');


const app = express();
const PORT = process.env.PORT || 3000;

app.use(bodyParser.json());
app.use(cors());

app.use(express.static(path.join(__dirname, '../frontend')));

// Use routes for API endpoints
app.use('/api/auth', authRoutes);
app.use('/api/user', userRoutes);
app.use('/api/sentiment', sentimentRoutes);
app.use('/api/predictions', predictionsRoutes);
app.use('/api/chart', chartRoutes);
app.use('/api/recommendations', recommendationsRoutes);
app.use('/api/tickers', tickersRoutes);

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/landing-page/landingPage.html'));
});

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/landing-page/landingPage.html'));
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
