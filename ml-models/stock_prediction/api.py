import os
import sys
import json
import time
import random
import argparse
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf
from keras.models import Sequential, load_model
from keras.layers import Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
from keras.layers import LSTM as OriginalLSTM

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

def my_lstm(*args, **kwargs):
    kwargs.pop("time_major", None)
    return OriginalLSTM(*args, **kwargs)

# === Directory Setup ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
for d in (MODEL_DIR, DATA_DIR, CACHE_DIR):
    os.makedirs(d, exist_ok=True)

DATA_REFRESH_DAYS = 3
CACHE_EXPIRY_DAYS = 7
UNRELIABLE_PATH = os.path.join(DATA_DIR, "unreliable_stocks.json")


index_funds = {
    "VFIAX", "SPY", "VOO", "VTSAX", "QQQ", "DIA", "IVV",
    "SCHX", "ITOT", "VGT", "VUG", "IWF", "FTEC", "XLK",
    "VTI", "VXUS", "VT", "VYM", "SCHD", "IWD", "IVW",
    "IJH", "IJR", "IWB", "RSP", "VO", "VB", "VBR",
    "VOOG", "VOOV", "VTHR", "IWV", "IWM", "VTV", "VTWO",
    "SPYG", "SPYV", "SPLG", "SCHB", "BND",
}

large_caps = {
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "BRK.B", "JPM", "V", "UNH", "XOM", "JNJ", "PG", "HD", "MA", "CVX", "LLY", "PFE", "ABBV", "PEP", "KO", "MRK",
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
    "NKTR", "FSLR", "QS", "DNA", "PSTG", "OKTA", "W", "TDOC",
    "BB", "CRSP", "EDIT", "BEAM", "OPEN", "Z", "RDFN"
}
extra_high_volatility = {
    "GME", "AMC", "BBBY", "CVNA", "NKLA",
    "AI", "SI", "CLSK", "HUDI", "OSTK",
    "SOUN", "FFIE",  "UPST", "FUBO",
    "NVAX", "VERU", "IONQ", "BEEM", "CLOV",
    "DWAC", "BBIG", "CEI", "MULN", "APE"
}
btc_sensitive = {
    "MSTR", "COIN", "RIOT", "MARA", "HUT", "BITF",
    "BTBT", "HIVE", "CLSK", "WULF", "SDIG",
    "GBTC", "BITO", "BKKT", "ARBK", "CORZ"
}

# === Cache Functions ===
def get_cached_prediction(ticker):
    cache_path = os.path.join(CACHE_DIR, f"{ticker}_forecast.json")
    if not os.path.exists(cache_path):
        return None
    with open(cache_path) as f:
        data = json.load(f)
    ts = data.get("timestamp")
    if not ts:
        return None
    if datetime.fromisoformat(ts) < datetime.now() - timedelta(days=CACHE_EXPIRY_DAYS):
        return None
    return data


def save_cached_prediction(ticker, one_month, six_month, idx):
    path = os.path.join(CACHE_DIR, f"{ticker}_forecast.json")
    out = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "1M": {"low": one_month["lower_bound"][-1], "median": one_month["median_prediction"][-1], "high": one_month["upper_bound"][-1]},
        "3M": {"low": six_month["lower_bound"][idx], "median": six_month["median_prediction"][idx], "high": six_month["upper_bound"][idx]},
        "6M": {"low": six_month["lower_bound"][-1], "median": six_month["median_prediction"][-1], "high": six_month["upper_bound"][-1]}
    }
    with open(path, 'w') as f:
        json.dump(out, f, indent=2)

# === Data and Model ===
def fetch_stock_data(ticker):
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < DATA_REFRESH_DAYS*86400:
        return
    df = yf.Ticker(ticker).history(period="5y")
    if df.empty:
        return
    df.to_csv(path)


def train_lstm_model(ticker):
    fetch_stock_data(ticker)
    df = pd.read_csv(os.path.join(DATA_DIR, f"{ticker}.csv"))
    scaler = MinMaxScaler((0,1))
    data = scaler.fit_transform(df["Close"].values.reshape(-1,1))
    X, y = [], []
    for i in range(60, len(data)-30):
        X.append(data[i-60:i,0]); y.append(data[i+30,0])
    X, y = np.array(X), np.array(y)
    X = X.reshape(*X.shape,1)
    model = Sequential([my_lstm(50, return_sequences=True, input_shape=(60,1)), Dropout(0.2), my_lstm(50), Dropout(0.2), Dense(1)])
    model.compile('adam','mean_squared_error')
    model.fit(X, y, epochs=5, batch_size=16, verbose=0)
    model.save(os.path.join(MODEL_DIR, f"{ticker}_model.h5"))


def is_pretrained(ticker):
    return os.path.exists(os.path.join(MODEL_DIR, f"{ticker}_model.h5")) and os.path.exists(os.path.join(DATA_DIR, f"{ticker}.csv"))


def log_unreliable_stock(ticker, reason):
    if not os.path.exists(UNRELIABLE_PATH):
        json.dump({"unstable_stocks": []}, open(UNRELIABLE_PATH,'w'))
    data = json.load(open(UNRELIABLE_PATH))
    data.setdefault("unstable_stocks",[])
    if ticker not in data["unstable_stocks"]:
        data["unstable_stocks"].append(ticker)
        json.dump(data, open(UNRELIABLE_PATH,'w'), indent=2)


def sample_predictions(arr, step):
    return arr[::step]




def predict_with_lstm(ticker, days=180, simulations=8):
    np.random.seed(42)
    random.seed(42)
    model = load_model(os.path.join(MODEL_DIR, f"{ticker}_model.h5"))
    df = pd.read_csv(os.path.join(DATA_DIR, f"{ticker}.csv"))
    scaler = MinMaxScaler(feature_range=(0,1))
    scaled_data = scaler.fit_transform(df["Close"].values.reshape(-1,1))
    last_60_days = scaled_data[-60:]
    X_input = np.reshape(last_60_days, (1, 60, 1))
    future_predictions = []
    last_real_price = df["Close"].iloc[-1]
    volatility = np.std(df["Close"].pct_change().dropna())

    # Determine volatility multipliers
    if ticker in index_funds:
        volatility_multiplier = 0.6; max_growth_range = (1.5, 2.5); min_decline_range = (1.5, 2.5)
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
    parser.add_argument('--ticker',required=True)
    args=parser.parse_args()
    t = args.ticker.strip().upper()

    cached = get_cached_prediction(t)
    if cached:
        print(json.dumps(cached)); sys.exit(0)

    if not is_pretrained(t):
        try: train_lstm_model(t)
        except Exception as e:
            log_unreliable_stock(t,str(e))
            print(json.dumps({'error':str(e)})); sys.exit(1)

    one = predict_with_lstm(t,30)
    six = predict_with_lstm(t,180)
    idx = len(six['median_prediction'])//2
    save_cached_prediction(t,one,six,idx)
    out={'predictions':{'1M':one['median_prediction'][-1],'3M':six['median_prediction'][idx],'6M':six['median_prediction'][-1]}}
    print(json.dumps(out))

