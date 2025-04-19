const express = require('express');
const router = express.Router();
const { spawn } = require('child_process');
const path = require('path');
const User = require('../models/User');

router.get('/', async (req, res) => {
  const email = req.query.email;
  if (!email) {
    return res.status(400).json({ error: 'Email parameter is required.' });
  }
  try {
    // Retrieve user from the database
    const user = await User.findOne({ email });
    if (!user) {
      return res.status(404).json({ error: 'User not found.' });
    }
    
    // Extract risk tolerance and investment preferences 
    const riskTolerance = user.riskTolerance;
    const preferencesArray = user.investmentPreferences;
    
    if (!riskTolerance || !preferencesArray || !preferencesArray.length) {
      return res.status(400).json({ error: 'User risk tolerance or investment preferences are not set.' });
    }
    
    const preferences = preferencesArray.join(",");
    
    const pythonScriptPath = path.join(__dirname, '..', '..', 'ml-models', 'stock_recommendations', 'recommendations.py');
    
    const pythonProcess = spawn('python', ['-u', pythonScriptPath, '--risk-level', riskTolerance, '--sectors', preferences]);
    
    let resultData = "";
    pythonProcess.stdout.on('data', (data) => {
      resultData += data.toString();
    });
    pythonProcess.stderr.on('data', (data) => {
      console.error(`stderr: ${data.toString()}`);
    });
    pythonProcess.on('close', (code) => {
      console.log("Raw output from Python:", resultData);
      if (resultData.trim() === "") {
        return res.status(500).json({ error: "No output from Python script." });
      }
      try {
        const result = JSON.parse(resultData);
        res.json(result);
      } catch (err) {
        console.error("Error parsing JSON:", err);
        res.status(500).json({ error: "Error parsing recommendations output." });
      }
    });
  } catch (error) {
    console.error("Error in recommendations route:", error);
    res.status(500).json({ error: "Internal server error." });
  }
});

module.exports = router;
