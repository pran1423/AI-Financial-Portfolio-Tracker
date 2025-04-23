
const express = require('express');
const router = express.Router();
const fs     = require('fs');
const path   = require('path');

const DATA_DIR = path.join(__dirname, '..', '..', 'ml-models', 'stock_prediction', 'data');

router.get('/', (req, res) => {
  fs.readdir(DATA_DIR, (err, files) => {
    if (err) {
      console.error("Error reading tickers directory:", err);
      return res.status(500).json({ error: "Could not list tickers." });
    }
    const tickers = files
      .filter(f => f.toLowerCase().endsWith('.csv'))
      .map(f => f.slice(0, -4).toUpperCase())
      .sort();
    res.json({ tickers });
  });
});

module.exports = router;
