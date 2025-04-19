import sys
import pandas as pd
import numpy as np
import os
import random
import json
import time
import argparse
from datetime import datetime, timedelta
from keras.models import Sequential, load_model
from keras.layers import Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
import yfinance as yf
from keras.layers import LSTM as OriginalLSTM

def my_lstm(*args, **kwargs):
    kwargs.pop("time_major", None)
    return OriginalLSTM(*args, **kwargs)

# === Directory Setup ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

DATA_REFRESH_DAYS = 3
CACHE_EXPIRY_DAYS = 7
UNRELIABLE_PATH = os.path.join(DATA_DIR, "unreliable_stocks.json")

# === Ticker Categories ===
index_funds = {
    "VFIAX", "SPY", "VOO", "VTSAX", "QQQ", "DIA", "IVV", 
    "SCHX", "ITOT", "VGT", "VUG", "IWF", "FTEC", "XLK",
    "VTI", "VXUS", "VT", "VYM", "SCHD", "IWD", "IVW",
    "IJH", "IJR", "IWB", "RSP", "VO", "VB", "VBR",
    "VOOG", "VOOV", "VTHR", "IWV", "IWM", "VTV", "VTWO",
    "SPYG", "SPYV", "SPLG", "SCHB", "BND"
}

large_caps = {
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", 
    "BRK.B", "JPM", "V", "UNH", "XOM", "JNJ", "PG", "HD",
    "MA", "CVX", "LLY", "PFE", "ABBV", "PEP", "KO", "MRK",
    "NFLX", "ADBE", "COST", "TMO", "AVGO", "INTC", "ORCL",
    "AMD", "DIS", "CMCSA", "NKE", "TXN", "QCOM", "IBM",
    "UPS", "GS", "MS", "CAT", "HON", "DHR", "AMGN", "BA",
    "DE", "C", "BKNG", "LMT", "MDT", "ISRG", "NOW", "ADP",
    "SPGI", "BLK", "SYK", "MO", "FDX", "T", "VRTX", "PGR"
}

high_volatility = {
    "TSLA", "NVDA", "ARKK", "RIVN", "PLTR", "SPCE", "SOFI", "HOOD", "AFRM",
    "SNOW", "CRWD", "ZS", "DOCU", "U", "ROKU", "FSLY", "NET",
    "SHOP", "SQ", "LCID", "NIO", "XPEV", "UPST", "BIDU", "DDOG", "TWLO",
    "PATH", "SE", "PYPL", "ASML", "BILI", "FUBO", "RUN", "ENPH", "BLNK",
    "NKTR", "FSLR", "QS", "DNA", "IONQ", "PSTG", "OKTA", "W", "TDOC",
    "BB", "CRSP", "EDIT", "BEAM", "OPEN", "Z", "RDFN"
}

extra_high_volatility = {
    "MARA", "RIOT", "COIN", "GME", "AMC", "BBBY", "CVNA", "NKLA",
    "AI", "HUT", "BITF", "SI", "CLSK", "HUDI", "OSTK"
}

btc_sensitive = {
    "MSTR", "COIN", "RIOT", "MARA", "HUT", "BITF"
}

# === Cache Functions ===
def get_cached_prediction(ticker):
    cache_path = os.path.join(CACHE_DIR, f"{ticker}_forecast.json")
    if not os.path.exists(cache_path):
        return None
    with open(cache_path, "r") as f:
        try:
            data = json.load(f)
            timestamp_str = data.get("timestamp")
            if not timestamp_str:
                return None
            timestamp = datetime.fromisoformat(timestamp_str)
            if datetime.now() - timestamp > timedelta(days=CACHE_EXPIRY_DAYS):
                print(f"Cache expired for {ticker}", file=sys.stderr)
                return None
            print(f"Loaded cached prediction for {ticker}", file=sys.stderr)
            return data
        except Exception as e:
            print(f"Failed to load cache for {ticker}: {e}", file=sys.stderr)
            return None

def save_cached_prediction(ticker, one_month, six_month, idx):
    cache_path = os.path.join(CACHE_DIR, f"{ticker}_forecast.json")
    data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "1M": {
            "low": one_month["lower_bound"][-1],
            "median": one_month["median_prediction"][-1],
            "high": one_month["upper_bound"][-1]
        },
        "3M": {
            "low": six_month["lower_bound"][idx],
            "median": six_month["median_prediction"][idx],
            "high": six_month["upper_bound"][idx]
        },
        "6M": {
            "low": six_month["lower_bound"][-1],
            "median": six_month["median_prediction"][-1],
            "high": six_month["upper_bound"][-1]
        }
    }
    with open(cache_path, "w") as f:
        json.dump(data, f, indent=4)

# === Data and Model Functions ===
def fetch_stock_data(ticker):
    file_path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if os.path.exists(file_path):
        file_age_days = (time.time() - os.path.getmtime(file_path)) / (60 * 60 * 24)
        if file_age_days < DATA_REFRESH_DAYS:
            print(f"{ticker} data is up-to-date. Skipping download.", file=sys.stderr)
            return
    print(f"Downloading updated {ticker} data...", file=sys.stderr)
    stock = yf.Ticker(ticker)
    df = stock.history(period="5y")
    if df.empty:
        print(f"ERROR: No stock data found for {ticker}", file=sys.stderr)
        return
    df.to_csv(file_path, index=True)
    print(f"Updated {ticker} data saved.", file=sys.stderr)

def train_lstm_model(ticker):
    file_path = os.path.join(DATA_DIR, f"{ticker}.csv")
    fetch_stock_data(ticker)
    df = pd.read_csv(file_path)
    if "Close" not in df.columns:
        raise ValueError(f"Invalid data format for {ticker}")
    scaler = MinMaxScaler(feature_range=(0,1))
    scaled_data = scaler.fit_transform(df["Close"].values.reshape(-1,1))
    X_train, y_train = [], []
    for i in range(60, len(scaled_data)-30):
        X_train.append(scaled_data[i-60:i, 0])
        y_train.append(scaled_data[i+30, 0])
    X_train, y_train = np.array(X_train), np.array(y_train)
    X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], 1))
    model = Sequential([
        my_lstm(50, return_sequences=True, input_shape=(X_train.shape[1], 1)),
        Dropout(0.2),
        my_lstm(50, return_sequences=False),
        Dropout(0.2),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')
    model.fit(X_train, y_train, epochs=5, batch_size=16)
    model_path = os.path.join(MODEL_DIR, f"{ticker}_model.h5")
    model.save(model_path)
    print(f"Trained & saved model for {ticker}", file=sys.stderr)

def is_pretrained(ticker):
    model_path = os.path.join(MODEL_DIR, f"{ticker}_model.h5")
    data_path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(model_path) or not os.path.exists(data_path):
        return False
    file_age_days = (time.time() - os.path.getmtime(data_path)) / (60 * 60 * 24)
    return file_age_days < DATA_REFRESH_DAYS

def log_unreliable_stock(ticker, reason="Unstable prediction behavior"):
    if not os.path.exists(UNRELIABLE_PATH):
        with open(UNRELIABLE_PATH, "w") as f:
            json.dump({"unstable_stocks": []}, f, indent=4)
    with open(UNRELIABLE_PATH, "r") as f:
        data = json.load(f)
    if ticker not in data.get("unstable_stocks", []):
        data["unstable_stocks"].append(ticker)
        with open(UNRELIABLE_PATH, "w") as f:
            json.dump(data, f, indent=4)
    print(f"Logged {ticker} as unreliable due to: {reason}", file=sys.stderr)

def sample_predictions(pred_list, step=10):
    return pred_list[::step]

def predict_with_lstm(ticker, days=180, simulations=8):
    np.random.seed(42)
    random.seed(42)
    model = load_model(os.path.join(MODEL_DIR, f"{ticker}_model.h5"), custom_objects={"LSTM": my_lstm})
    df = pd.read_csv(os.path.join(DATA_DIR, f"{ticker}.csv"))
    scaler = MinMaxScaler(feature_range=(0,1))
    scaled_data = scaler.fit_transform(df["Close"].values.reshape(-1,1))
    last_60_days = scaled_data[-60:]
    X_input = np.reshape(last_60_days, (1, 60, 1))
    future_predictions = []
    last_real_price = df["Close"].iloc[-1]
    volatility = np.std(df["Close"].pct_change().dropna())

    if ticker in index_funds:
        volatility_multiplier = 0.5; max_growth_range = (1.5, 3.0); min_decline_range = (1.5, 3.0)
    elif ticker in large_caps:
        volatility_multiplier = 1.0; max_growth_range = (2.0, 4.0); min_decline_range = (2.0, 3.5)
    elif ticker in high_volatility:
        volatility_multiplier = 1.4; max_growth_range = (3.5, 5.5); min_decline_range = (3.0, 5.0)
    elif ticker in extra_high_volatility:
        volatility_multiplier = 2.0; max_growth_range = (4.5, 7.5); min_decline_range = (4.0, 6.5)
    elif ticker in btc_sensitive:
        volatility_multiplier = 1.6; max_growth_range = (2.5, 4.0); min_decline_range = (2.0, 3.0)
    else:
        volatility_multiplier = 1.2; max_growth_range = (2.5, 4.5); min_decline_range = (2.0, 4.0)

    expected_length = days // (1 if days <= 30 else 2)
    for _ in range(simulations):
        temp_input = X_input.copy()
        simulated_prices = []
        for t in range(expected_length):
            adjusted_multiplier = volatility_multiplier
            if days == 180 and t >= (expected_length // 2):
                adjusted_multiplier *= 1.1 + ((t - (expected_length // 2)) / (expected_length - (expected_length // 2))) * 0.2
            elif days == 30:
                adjusted_multiplier *= 1 + (0.2 * (t / expected_length))
            predicted_scaled = model.predict(temp_input, batch_size=days)
            predicted_price = scaler.inverse_transform(predicted_scaled)[0][0]
            scale_factor = max(1e-6, np.clip(volatility * np.random.uniform(1.5, 3.5) * adjusted_multiplier, 0.01, 0.15))
            noise = np.random.normal(loc=0, scale=predicted_price * scale_factor)
            predicted_price = max(1e-3, predicted_price + noise)
            max_growth = 1 + (volatility * np.random.uniform(*max_growth_range) * adjusted_multiplier)
            min_drop = 1 - (volatility * np.random.uniform(*min_decline_range) * adjusted_multiplier)
            predicted_price = np.clip(predicted_price, last_real_price * min_drop, last_real_price * max_growth)
            simulated_prices.append(predicted_price)
            temp_input = np.roll(temp_input, shift=-1, axis=1)
            temp_input[:, -1, 0] = (0.3 * temp_input[:, -3, 0]) + (0.3 * temp_input[:, -2, 0]) + (0.4 * predicted_scaled[0, 0])
        future_predictions.append(simulated_prices)

    future_predictions = np.array(future_predictions)
    std_dev = np.std(future_predictions, axis=0)
    if np.any(std_dev < 0) or np.any(np.isnan(std_dev)):
        log_unreliable_stock(ticker, "Negative or NaN standard deviation")
        raise ValueError(f"{ticker} predictions are unreliable.")
    lower_bound = np.percentile(future_predictions, 5, axis=0) - (0.2 * std_dev)
    median_pred = np.percentile(future_predictions, 50, axis=0)
    upper_bound = np.percentile(future_predictions, 95, axis=0) + (0.1 * std_dev)
    if days == 180:
        drop = (median_pred[0] - median_pred[-1]) / median_pred[0]
        if drop > 0.5:
            log_unreliable_stock(ticker, f"6M drop {drop:.2%}")
            raise ValueError("6M median prediction dropped too much.")
    if days == 30 and (ticker in btc_sensitive or ticker in high_volatility):
        growth = (median_pred[-1] - median_pred[0]) / median_pred[0]
        if growth > 0.35:
            log_unreliable_stock(ticker, f"1M growth too high: {growth:.2%}")
            raise ValueError("1M prediction too optimistic.")
    return {
        "median_prediction": sample_predictions(median_pred.tolist(), step=5 if days == 30 else 3),
        "lower_bound": sample_predictions(lower_bound.tolist(), step=5 if days == 30 else 3),
        "upper_bound": sample_predictions(upper_bound.tolist(), step=5 if days == 30 else 3)
    }

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ticker', type=str, required=True, help='Stock ticker symbol')
    args = parser.parse_args()
    ticker = args.ticker.strip().upper()

    cached = get_cached_prediction(ticker)
    if cached:
        print(json.dumps(cached))
        exit()

    if not is_pretrained(ticker):
        try:
            train_lstm_model(ticker)
        except Exception as e:
            print(json.dumps({"error": "Training failed: " + str(e)}))
            exit(1)
    try:
        one_month = predict_with_lstm(ticker, days=30)
        six_month = predict_with_lstm(ticker, days=180)
        idx = len(six_month["median_prediction"]) // 2
        save_cached_prediction(ticker, one_month, six_month, idx)
        result = {
            "predictions": {
                "1M": one_month["median_prediction"][-1],
                "3M": six_month["median_prediction"][idx],
                "6M": six_month["median_prediction"][-1]
            }
        }
        print(json.dumps(result))
    except Exception as e:
        log_unreliable_stock(ticker, str(e))
        print(json.dumps({"error": str(e)}))
