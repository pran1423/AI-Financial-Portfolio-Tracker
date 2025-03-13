'''import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
import os

DATA_DIR = "ml-models/stock_prediction/data"

def quick_estimate(ticker, days=30):
    """Use Ridge Regression to quickly estimate future prices."""
    file_path = os.path.join(DATA_DIR, f"{ticker}.csv")
    df = pd.read_csv(file_path)

    # Prepare dataset (Using Close Price)
    df["Days"] = np.arange(len(df))  
    X = df[["Days"]].values
    y = df["Close"].values

    # Train Ridge Regression Model
    model = Ridge()
    model.fit(X, y)

    # Predict next `days` days
    future_days = np.array([[len(df) + i] for i in range(days)])
    future_prices = model.predict(future_days)

    return {"ticker": ticker, "predicted_prices": future_prices.tolist()}
# Estimate for AAPL, MSFT, TSLA'''


