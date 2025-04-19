
const express = require('express');
const router = express.Router();
const bcrypt = require('bcrypt');
const mongoose = require('../../database/db');
const User = require('../models/User');

// Create Account Route 
router.post('/create-account', async (req, res) => {
  console.log('Received create-account request');
  console.log('Mongoose readyState:', mongoose.connection.readyState);

  const { email, password, confirmPassword } = req.body;
  if (!email || !password || !confirmPassword) {
    return res.status(400).json({ error: 'All fields are required.' });
  }
  if (password !== confirmPassword) {
    return res.status(400).json({ error: 'Passwords do not match.' });
  }
  try {
    const existingUser = await User.findOne({ email });
    if (existingUser) {
      return res.status(400).json({ error: 'Email already registered.' });
    }
    const hashedPassword = await bcrypt.hash(password, 10);
    const newUser = new User({ email, password: hashedPassword });
    await newUser.save();
    return res.status(201).json({ message: 'Account created successfully!' });
  } catch (error) {
    console.error('Error creating account:', error);
    return res.status(500).json({ error: 'Internal server error.' });
  }
});

// LOGIN Route
router.post('/login', async (req, res) => {
  try {
    const { email, password } = req.body;
    if (!email || !password) {
      return res.status(400).json({ error: 'Missing email or password.' });
    }
    const user = await User.findOne({ email });
    if (!user) {
      return res.status(404).json({ error: 'User not found. Please create an account.' });
    }
    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) {
      return res.status(400).json({ error: 'Invalid credentials.' });
    }
    return res.status(200).json({ message: 'Login successful!', user });
  } catch (error) {
    console.error('Error during login:', error);
    return res.status(500).json({ error: 'Internal server error.' });
  }
});

module.exports = router;
