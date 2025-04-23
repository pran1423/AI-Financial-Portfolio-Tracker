
const mongoose = require('../../database/db');

const userSchema = new mongoose.Schema({
  email: { type: String, required: true, unique: true },
  password: { type: String, required: true },
  riskTolerance: { type: String, default: 'not set' },
  investmentPreferences: { type: [String], default: [] },
  termsApproved: { type: Boolean, default: false },

  
  investments: {
    type: [{
      ticker: { type: String },
      datePurchased: { type: Date },
      shares: { type: Number },
      sharePrice: { type: Number }
    }],
    default: []
  }
});

userSchema.index({ email: 1 });

module.exports = mongoose.model('User', userSchema);
