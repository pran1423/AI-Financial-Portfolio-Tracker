from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
import os
import random
from keras.models import Sequential, load_model
from keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
import yfinance as yf


MODEL_DIR = "ml-models/stock_prediction/models"
DATA_DIR = "ml-models/stock_prediction/data"
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)





def fetch_stock_data(ticker):

    file_path = os.path.join(DATA_DIR, f"{ticker}.csv")

    if os.path.exists(file_path):
        print(f" {ticker} data already exists.")
        return
    
    print(f" Downloading {ticker} data...")
    stock = yf.Ticker(ticker)
    df = stock.history(period="5y")

    if df.empty:
        raise ValueError(f" No stock data found for {ticker}")

    df.to_csv(file_path)
    print(f" Downloaded & saved {ticker} data.")

def train_lstm_model(ticker):
    
    file_path = os.path.join(DATA_DIR, f"{ticker}.csv")


    if not os.path.exists(file_path):
        fetch_stock_data(ticker)

    df = pd.read_csv(file_path)

  
    scaler = MinMaxScaler(feature_range=(0,1))
    scaled_data = scaler.fit_transform(df["Close"].values.reshape(-1,1))

    X_train, y_train = [], []
    for i in range(60, len(scaled_data)-30):  
        X_train.append(scaled_data[i-60:i, 0])
        y_train.append(scaled_data[i+30, 0])  

    X_train, y_train = np.array(X_train), np.array(y_train)
    X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], 1))

    
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=(X_train.shape[1], 1)),
        Dropout(0.2),
        LSTM(50, return_sequences=False),
        Dropout(0.2),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')

    
    model.fit(X_train, y_train, epochs=5, batch_size=16)

    
    model.save(f"{MODEL_DIR}/{ticker}_model.h5")
    print(f" Trained & saved {ticker} model.")

def is_pretrained(ticker):
    
    return os.path.exists(f"{MODEL_DIR}/{ticker}_model.h5")

def sample_predictions(pred_list, step=10):
    
    return pred_list[::step]  




index_funds = {
    "VFIAX", "SPY", "VOO", "VTSAX", "QQQ", "DIA", "IVV", 
    "SCHX", "ITOT", "VGT", "VUG", "IWF", "FTEC", "XLK",
    "VTI", "VXUS", "VT", "VYM", "SCHD", "IWD", "IVW",
    "IJH", "IJR", "IWB", "RSP", "VO", "VB", "VBR"
}

large_caps = {
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", 
    "BRK.B", "JPM", "V", "UNH", "XOM", "JNJ", "PG", "HD",
    "MA", "CVX", "LLY", "PFE", "ABBV", "PEP", "KO", "MRK",
    "NFLX", "ADBE", "COST", "TMO", "AVGO", "INTC", "ORCL",
    "AMD", "DIS", "CMCSA", "NKE", "TXN", "QCOM", "IBM",
    "UPS", "GS", "MS", "CAT", "HON", "DHR", "AMGN", "BA"
}

high_volatility = {
    "TSLA", "NVDA", "ARKK", "COIN", "RIVN", "PLTR", "SPCE",
    "SOFI", "HOOD", "AFRM", "SNOW", "CRWD", "ZS", "DOCU",
    "U", "ROKU", "FSLY", "NET", "MSTR", "SHOP", "SQ",
    "LCID", "NIO", "XPEV", "NKLA", "UPST", "BIDU", "DDOG",
    "TWLO", "PATH", "MARA", "RIOT", "SE", "PYPL", "ASML"
}


def predict_with_lstm(ticker, days=180, simulations=8):
    np.random.seed(42)
    random.seed(42)

    model = load_model(f"{MODEL_DIR}/{ticker}_model.h5")
    df = pd.read_csv(f"{DATA_DIR}/{ticker}.csv")

    scaler = MinMaxScaler(feature_range=(0,1))
    scaled_data = scaler.fit_transform(df["Close"].values.reshape(-1,1))

    last_60_days = scaled_data[-60:]
    X_input = np.reshape(last_60_days, (1, 60, 1))

    future_predictions = []
    last_real_price = df["Close"].iloc[-1]
    volatility = np.std(df["Close"].pct_change().dropna())

  
    if ticker in index_funds:
        volatility_multiplier = 0.5  
    elif ticker in large_caps:
        volatility_multiplier = 1.0  
    elif ticker in high_volatility:
        volatility_multiplier = 2.0  
    else:
        volatility_multiplier = 1.0  

    expected_length = days // (1 if days <= 30 else 2)

    for _ in range(simulations):
        temp_input = X_input.copy()
        simulated_prices = []

     

        for _ in range(expected_length):  
            predicted_scaled = model.predict(temp_input, batch_size=days)
            predicted_price = scaler.inverse_transform(predicted_scaled)[0][0]

      
            scale_factor = np.clip(volatility * np.random.uniform(1.5, 3.5) * volatility_multiplier, 0.01, 0.15)
            noise = np.random.normal(loc=0, scale=predicted_price * scale_factor)
            predicted_price += noise 
            
           
            max_growth_factor = 1 + (volatility * np.random.uniform(4.0, 7.0) * volatility_multiplier)
            min_growth_factor = 1 - (volatility * np.random.uniform(3.5, 6.0) * volatility_multiplier)

            predicted_price = np.clip(predicted_price, last_real_price * min_growth_factor, last_real_price * max_growth_factor)

            simulated_prices.append(predicted_price)

            temp_input = np.roll(temp_input, shift=-1, axis=1)
            temp_input[:, -1, 0] = (0.3 * temp_input[:, -3, 0]) + (0.3 * temp_input[:, -2, 0]) + (0.4 * predicted_scaled[0, 0])

        if len(simulated_prices) < expected_length:
            simulated_prices += [simulated_prices[-1]] * (expected_length - len(simulated_prices))  

        future_predictions.append(simulated_prices)

    future_predictions = np.array(future_predictions)  
    std_dev = np.std(future_predictions, axis=0)

    lower_bound = np.percentile(future_predictions, 5, axis=0) - (0.2 * std_dev)  
    median_pred = np.percentile(future_predictions, 50, axis=0)  
    upper_bound = np.percentile(future_predictions, 95, axis=0) + (0.1 * std_dev)

    return {
        "median_prediction": sample_predictions(median_pred.tolist(), step=5 if days == 30 else 3),  
        "lower_bound": sample_predictions(lower_bound.tolist(), step=5 if days == 30 else 3),
        "upper_bound": sample_predictions(upper_bound.tolist(), step=5 if days == 30 else 3)
    }





@app.route('/predict_stock', methods=['GET'])
def predict_stock():
    ticker = request.args.get("ticker")
    
    if not ticker:
        return jsonify({"error": "Ticker parameter is required"}), 400

    if not is_pretrained(ticker):
        print(f" {ticker} model not found. Training now...")
        try:
            train_lstm_model(ticker)  
        except Exception as e:
            return jsonify({"error": f"Failed to train model: {str(e)}"}), 500

    try:
        one_month_prediction = predict_with_lstm(ticker, days=30)
        six_month_prediction = predict_with_lstm(ticker, days=180)


        step=5

        response = {
            "ticker": ticker,
            "summary": {
                "1M": [one_month_prediction["lower_bound"][-1], one_month_prediction["upper_bound"][-1]],
                "6M": [six_month_prediction["lower_bound"][-1], six_month_prediction["upper_bound"][-1]]
            },
            "detailed": {
                "1M": {
                    "lower_bound": sample_predictions(one_month_prediction["lower_bound"], step),
                    "median_prediction": sample_predictions(one_month_prediction["median_prediction"], step),
                    "upper_bound": sample_predictions(one_month_prediction["upper_bound"], step)
                },
                "6M": {
                    "lower_bound": sample_predictions(six_month_prediction["lower_bound"], step),
                    "median_prediction": sample_predictions(six_month_prediction["median_prediction"], step),
                    "upper_bound": sample_predictions(six_month_prediction["upper_bound"], step)
                }
            }
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True)
