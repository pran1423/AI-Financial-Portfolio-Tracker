
const express = require('express');
const router = express.Router();
const { spawn } = require('child_process');
const path = require('path');

router.get('/', (req, res) => {
    const stockSymbol = req.query.stock || 'AAPL';
    const pythonScriptPath = path.join(__dirname, '../../ml-models/sentiment_analysis/FinBert.py');

    const pythonProcess = spawn('python', [pythonScriptPath, stockSymbol]);

    let resultData = "";
    pythonProcess.stdout.on('data', (data) => {
        resultData += data.toString();
    });
    pythonProcess.stderr.on('data', (data) => {
        console.error(`stderr: ${data}`);
    });
    pythonProcess.on('close', (code) => {
        try {
            const result = JSON.parse(resultData);
            res.json(result);
        } catch (err) {
            console.error('Error parsing JSON:', err);
            res.status(500).json({ error: 'Error parsing sentiment analysis output.' });
        }
    });
});

module.exports = router;
