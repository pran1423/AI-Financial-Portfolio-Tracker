const express = require('express');
const router = express.Router();
const yf = require('yahoo-finance2').default;

router.get('/', async (req, res) => {
  const { ticker } = req.query;
  if (!ticker) {
    return res.status(400).json({ error: 'Ticker parameter is required.' });
  }
  try {
    // Fetch historical data
    const period1 = new Date(new Date().setMonth(new Date().getMonth() - 6));
    const period2 = new Date();
    const queryOptions = {
      period1: period1.toISOString(),
      period2: period2.toISOString(),
      interval: '1d'
    };
    const historicalData = await yf.historical(ticker, queryOptions);
    if (historicalData && historicalData.length > 0) {
      const labels = historicalData.map(item => new Date(item.date).toISOString().split('T')[0]);
      const prices = historicalData.map(item => item.close);
      return res.json({ labels, prices });
    }
    return res.status(404).json({ error: 'No historical data found for ticker ' + ticker });
  } catch (error) {
    console.error("Error fetching chart data for ticker:", ticker, error);
    return res.status(500).json({ error: 'Internal server error.' });
  }
});

module.exports = router;
