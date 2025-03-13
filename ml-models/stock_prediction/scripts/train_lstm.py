import pandas as pd
import numpy as np
import os
from keras.models import Sequential, load_model
from keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
import yfinance as yf

# Directories
MODEL_DIR = "ml-models/stock_prediction/models"
DATA_DIR = "ml-models/stock_prediction/data"
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


def fetch_stock_data(ticker):
    
    file_path = os.path.join(DATA_DIR, f"{ticker}.csv")

    if os.path.exists(file_path):
        print(f"✅ {ticker} data already exists.")
        return

    print(f" Downloading {ticker} data...")
    stock = yf.Ticker(ticker)
    df = stock.history(period="5y")

    if df.empty:
        raise ValueError(f" No stock data found for {ticker}")

    df.to_csv(file_path)
    print(f"✅ Downloaded & saved {ticker} data.")


def train_lstm_model(ticker):
    file_path = os.path.join(DATA_DIR, f"{ticker}.csv")

    if not os.path.exists(file_path):
        fetch_stock_data(ticker)

    df = pd.read_csv(file_path)

    # Preprocess Data
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(df["Close"].values.reshape(-1, 1))

    X_train, y_train = [], []
    for i in range(60, len(scaled_data) - 30):
        X_train.append(scaled_data[i - 60 : i, 0])
        y_train.append(scaled_data[i + 30, 0])

    X_train, y_train = np.array(X_train), np.array(y_train)
    X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], 1))

    # Build LSTM Model
    model = Sequential(
        [
            LSTM(50, return_sequences=True, input_shape=(X_train.shape[1], 1)),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(1),
        ]
    )
    model.compile(optimizer="adam", loss="mean_squared_error")

    # Train Model
    model.fit(X_train, y_train, epochs=5, batch_size=16)

    # Save Model
    model.save(f"{MODEL_DIR}/{ticker}_model.h5")
    print(f"✅ Trained & saved {ticker} model.")


def predict_with_lstm(ticker, days=180, simulations=8):

    np.random.seed(42)
    model = load_model(f"{MODEL_DIR}/{ticker}_model.h5")
    df = pd.read_csv(f"{DATA_DIR}/{ticker}.csv")

    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(df["Close"].values.reshape(-1, 1))

    last_60_days = scaled_data[-60:]
    X_input = np.reshape(last_60_days, (1, 60, 1))

    future_predictions = []
    last_real_price = df["Close"].iloc[-1]
    volatility = np.std(df["Close"].pct_change().dropna())

    step_size = 1 if days == 30 else 2  
    expected_length = days // step_size  

    for _ in range(simulations):
        temp_input = X_input.copy()
        simulated_prices = []

        for _ in range(expected_length):
            predicted_scaled = model.predict(temp_input, batch_size=days)
            predicted_price = scaler.inverse_transform(predicted_scaled)[0][0]


            if days == 180:
                scale_factor = np.clip(volatility * np.random.uniform(1.5, 3.5), 0.01, 0.08)
            else:
                scale_factor = np.clip(volatility * np.random.uniform(0.8, 1.5), 0.005, 0.03)

            noise = np.random.normal(loc=0, scale=predicted_price * scale_factor)
            predicted_price += noise


            if days == 180:
                drift_factor = np.clip(volatility * np.random.uniform(0.02, 0.06), 0.01, 0.05)
                predicted_price += last_real_price * drift_factor

            simulated_prices.append(predicted_price)

            if len(simulated_prices) < expected_length:
                simulated_prices += [simulated_prices[-1]] * (expected_length - len(simulated_prices))

            temp_input = np.roll(temp_input, shift=-1, axis=1)
            temp_input[:, -1, 0] = (
                0.3 * temp_input[:, -3, 0] + 0.3 * temp_input[:, -2, 0] + 0.4 * predicted_scaled[0, 0]
            )

        future_predictions.append(simulated_prices)

    future_predictions = np.array(future_predictions)
    std_dev = np.std(future_predictions, axis=0)

    lower_bound = np.percentile(future_predictions, 5, axis=0) - (0.2 * std_dev)
    median_pred = np.percentile(future_predictions, 50, axis=0)
    upper_bound = np.percentile(future_predictions, 95, axis=0) + (0.1 * std_dev)

    return {
        "median_prediction": median_pred.tolist(),
        "lower_bound": lower_bound.tolist(),
        "upper_bound": upper_bound.tolist(),
    }


for stock in ["AAPL", "MSFT", "TSLA", "VFIAX"]:
    train_lstm_model(stock)
