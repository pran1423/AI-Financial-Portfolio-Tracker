import os
# suppress most TensorFlow logs (do this before any TF import)
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import sys
import pandas as pd
import numpy as np
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
        age = (time.time() - os.path.getmtime(file_path)) / (60*60*24)
        if age < DATA_REFRESH_DAYS:
            print(f"{ticker} data up-to-date; skipping download.", file=sys.stderr)
            return
    print(f"Downloading updated {ticker} data…", file=sys.stderr)
    stock = yf.Ticker(ticker)
    df = stock.history(period="5y")
    if df.empty:
        print(f"ERROR: No stock data for {ticker}", file=sys.stderr)
        return
    df.to_csv(file_path, index=True)
    print(f"Saved {ticker} data.", file=sys.stderr)

def train_lstm_model(ticker):
    file_path = os.path.join(DATA_DIR, f"{ticker}.csv")
    fetch_stock_data(ticker)
    df = pd.read_csv(file_path)
    if "Close" not in df.columns:
        raise ValueError(f"No Close column for {ticker}")
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled = scaler.fit_transform(df["Close"].values.reshape(-1,1))
    X, y = [], []
    for i in range(60, len(scaled)-30):
        X.append(scaled[i-60:i, 0])
        y.append(scaled[i+30, 0])
    X, y = np.array(X), np.array(y)
    X = X.reshape((X.shape[0], X.shape[1], 1))

    model = Sequential([
        my_lstm(50, return_sequences=True, input_shape=(60,1)),
        Dropout(0.2),
        my_lstm(50, return_sequences=False),
        Dropout(0.2),
        Dense(1)
    ])
    model.compile(optimizer="adam", loss="mean_squared_error")
    # <-- silent training:
    model.fit(X, y, epochs=5, batch_size=16, verbose=0)

    model_path = os.path.join(MODEL_DIR, f"{ticker}_model.h5")
    model.save(model_path)
    print(f"Trained & saved model for {ticker}", file=sys.stderr)

def is_pretrained(ticker):
    mp = os.path.join(MODEL_DIR, f"{ticker}_model.h5")
    dp = os.path.join(DATA_DIR,  f"{ticker}.csv")
    if not os.path.exists(mp) or not os.path.exists(dp):
        return False
    age = (time.time() - os.path.getmtime(dp)) / (60*60*24)
    return age < DATA_REFRESH_DAYS

def log_unreliable_stock(ticker, reason="Unstable"):
    if not os.path.exists(UNRELIABLE_PATH):
        json.dump({"unstable_stocks":[]}, open(UNRELIABLE_PATH,"w"), indent=4)
    data = json.load(open(UNRELIABLE_PATH))
    if ticker not in data["unstable_stocks"]:
        data["unstable_stocks"].append(ticker)
        json.dump(data, open(UNRELIABLE_PATH,"w"), indent=4)
    print(f"Logged {ticker} as unreliable: {reason}", file=sys.stderr)

def sample_predictions(lst, step=10):
    return lst[::step]

def predict_with_lstm(ticker, days=180, sims=8):
    np.random.seed(42); random.seed(42)
    model = load_model(os.path.join(MODEL_DIR, f"{ticker}_model.h5"),
                       custom_objects={"LSTM": my_lstm})
    df = pd.read_csv(os.path.join(DATA_DIR, f"{ticker}.csv"))
    scaler = MinMaxScaler(feature_range=(0,1))
    scaled = scaler.fit_transform(df["Close"].values.reshape(-1,1))
    last60 = scaled[-60:]
    inp = last60.reshape((1,60,1))
    last_price = df["Close"].iloc[-1]
    vol = np.std(df["Close"].pct_change().dropna())

    # choose multiplier ranges based on category...
    # (omitted here for brevity—but include yours)

    length = days // (1 if days<=30 else 2)
    sims_out = []
    for _ in range(sims):
        tmp = inp.copy(); preds = []
        for t in range(length):
            ps = model.predict(tmp, verbose=0)[0][0]
            price = scaler.inverse_transform([[ps]])[0][0]
            noise = np.random.normal(scale=price * vol * 0.1)
            price = max(0, price + noise)
            preds.append(price)
            tmp = np.roll(tmp, -1, axis=1)
            tmp[0,-1,0] = ps
        sims_out.append(preds)

    arr = np.array(sims_out)
    med = np.percentile(arr,50,axis=0)
    low = np.percentile(arr,5,axis=0)
    high= np.percentile(arr,95,axis=0)
    return {
        "median_prediction": sample_predictions(med.tolist(), 5 if days<=30 else 3),
        "lower_bound":        sample_predictions(low.tolist(),  5 if days<=30 else 3),
        "upper_bound":        sample_predictions(high.tolist(), 5 if days<=30 else 3)
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--ticker', required=True, help='Stock ticker')
    args = parser.parse_args()
    t = args.ticker.strip().upper()

    cached = get_cached_prediction(t)
    if cached:
        print(json.dumps(cached))
        sys.exit(0)

    if not is_pretrained(t):
        try:
            train_lstm_model(t)
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            sys.exit(1)

    try:
        one  = predict_with_lstm(t, days=30)
        six  = predict_with_lstm(t, days=180)
        idx  = len(six["median_prediction"])//2
        save_cached_prediction(t, one, six, idx)
        out = {
            "predictions": {
                "1M": one["median_prediction"][-1],
                "3M": six["median_prediction"][idx],
                "6M": six["median_prediction"][-1]
            }
        }
        print(json.dumps(out))
    except Exception as e:
        log_unreliable_stock(t, str(e))
        print(json.dumps({"error": str(e)}))
