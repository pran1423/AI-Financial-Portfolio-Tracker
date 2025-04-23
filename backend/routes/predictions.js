const express = require('express');
const router = express.Router();
const { exec } = require('child_process');
const path = require('path');

router.get('/', (req, res) => {
  const ticker = req.query.ticker;
  if (!ticker) {
    return res.status(400).json({ error: "Ticker parameter is required" });
  }

  const scriptPath = path.join(__dirname, '..', '..', 'ml-models', 'stock_prediction', 'api.py');
  
  const pythonCommand = process.platform === 'win32' ? 'python' : 'python3';
  const cmd = `${pythonCommand} "${scriptPath}" --ticker ${ticker}`;

  exec(cmd, (error, stdout, stderr) => {
    if (error) {
      console.error(`Error executing Python script: ${error}`);
      return res.status(500).json({ error: error.message });
    }
    try {
      const prediction = JSON.parse(stdout);
      res.json(prediction);
    } catch (parseError) {
      console.error(`Error parsing output: ${parseError}`);
      res.status(500).json({ error: "Error parsing prediction output" });
    }
  });
});

module.exports = router;
