
const express = require('express');
const router  = express.Router();
const yf      = require('yahoo-finance2').default;
const User    = require('../models/User');
require('dotenv').config(); // Load .env


// Fetch current live price
async function getStockPrice(ticker) {
  try {
    const quote = await yf.quote(ticker);
    return parseFloat(quote.regularMarketPrice);
  } catch (err) {
    console.error(`Error fetching price for ${ticker}:`, err.message);
    return null;
  }
}

// Fetch historical price on a given date
async function getHistoricalPrice(ticker, date) {
  try {
    const opts = { period1: date, interval: '1d' };
    const hist = await yf.historical(ticker, opts);
    if (hist && hist.length > 0) {
      return parseFloat(hist[0].close);
    }
    throw new Error('No historical data');
  } catch (err) {
    console.error(`Error fetching historical price for ${ticker} on ${date}:`, err.message);
    return null;
  }
}


router.get('/historical-price', async (req, res) => {
  const { ticker, date } = req.query;
  if (!ticker || !date) {
    return res.status(400).json({ error: 'Missing ticker or date parameter.' });
  }
  const price = await getHistoricalPrice(ticker, date);
  if (price === null) {
    return res.status(404).json({ error: 'No price data found for that date.' });
  }
  res.json({ ticker, date, price });
});


// Returns full user object, updating each investment's currentPrice
 
router.get('/get', async (req, res) => {
  try {
    const { email } = req.query;
    if (!email) return res.status(400).json({ error: 'Email is required.' });

    const user = await User.findOne({ email });
    if (!user) return res.status(404).json({ error: 'User not found.' });

    if (user.investments?.length) {
      for (let inv of user.investments) {
        const cp = await getStockPrice(inv.ticker);
        if (cp != null) inv.currentPrice = cp;
      }
      await user.save();
    }

    res.json({ user });
  } catch (err) {
    console.error('Error fetching user:', err);
    res.status(500).json({ error: 'Internal server error.' });
  }
});

// Returns only the investments array
router.get('/investments', async (req, res) => {
  try {
    const { email } = req.query;
    if (!email) return res.status(400).json({ error: 'Email is required.' });

    const user = await User.findOne({ email });
    if (!user) return res.status(404).json({ error: 'User not found.' });

    res.json({ investments: user.investments });
  } catch (err) {
    console.error('Error fetching investments:', err);
    res.status(500).json({ error: 'Internal server error.' });
  }
});


 // Returns the live current price for a ticker

router.get('/current-price', async (req, res) => {
  try {
    const { ticker } = req.query;
    if (!ticker) return res.status(400).json({ error: 'Ticker is required.' });

    const price = await getStockPrice(ticker);
    res.json({ ticker, currentPrice: price });
  } catch (err) {
    console.error('Error fetching current price:', err);
    res.status(500).json({ error: 'Internal server error.' });
  }
});


 // Save investments; auto‑fetch sharePrice if missing
 
router.post('/invest-info', async (req, res) => {
  try {
    const { email, investments } = req.body;
    if (!email || !Array.isArray(investments) || !investments.length) {
      return res.status(400).json({ error: 'Missing email or investments.' });
    }

    for (let inv of investments) {
      // auto‑fetch if no sharePrice
      if (!inv.sharePrice) {
        const hp = await getHistoricalPrice(inv.ticker, inv.datePurchased);
        inv.sharePrice = hp != null ? hp : 0;
      }
  
      if (inv.datePurchased) inv.datePurchased = new Date(inv.datePurchased);
    }

    const user = await User.findOneAndUpdate(
      { email },
      { investments },
      { new: true }
    );
    if (!user) return res.status(404).json({ error: 'User not found.' });

    res.json({
      message: 'Investments updated.',
      investments: user.investments
    });
  } catch (err) {
    console.error('Error updating investments:', err);
    res.status(500).json({ error: 'Internal server error.' });
  }
});


router.post('/approve-terms', async (req, res) => {
  try {
    const { email } = req.body;
    if (!email) return res.status(400).json({ error: 'Email is required.' });

    const user = await User.findOneAndUpdate(
      { email },
      { termsApproved: true },
      { new: true }
    );
    if (!user) return res.status(404).json({ error: 'User not found.' });

    res.json({ message: 'Terms approved.', user });
  } catch (err) {
    console.error('Error approving terms:', err);
    res.status(500).json({ error: 'Internal server error.' });
  }
});


router.post('/risk-tolerance', async (req, res) => {
  try {
    const { email, riskTolerance } = req.body;
    if (!email || !riskTolerance) {
      return res.status(400).json({ error: 'Missing fields.' });
    }

    const user = await User.findOneAndUpdate(
      { email },
      { riskTolerance },
      { new: true }
    );
    if (!user) return res.status(404).json({ error: 'User not found.' });

    res.json({
      message: 'Risk tolerance updated.',
      riskTolerance: user.riskTolerance
    });
  } catch (err) {
    console.error('Error updating risk tolerance:', err);
    res.status(500).json({ error: 'Internal server error.' });
  }
});

router.post('/investment-preferences', async (req, res) => {
  try {
    const { email, preferences } = req.body;
    if (!email || !preferences) {
      return res.status(400).json({ error: 'Missing fields.' });
    }

    const user = await User.findOneAndUpdate(
      { email },
      { investmentPreferences: preferences },
      { new: true }
    );
    if (!user) return res.status(404).json({ error: 'User not found.' });

    res.json({
      message: 'Preferences updated.',
      investmentPreferences: user.investmentPreferences
    });
  } catch (err) {
    console.error('Error updating preferences:', err);
    res.status(500).json({ error: 'Internal server error.' });
  }
});

module.exports = router;
