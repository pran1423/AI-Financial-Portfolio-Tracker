#!/usr/bin/env python
import yfinance as yf
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import random
import sys
import argparse

CACHE_FILE = "cached_sp500_stock_data.json"
CACHE_EXPIRY_DAYS = 1  
MAX_TOTAL_RECOMMENDATIONS = 10
MAX_PER_SECTOR = 2

def is_cache_valid():
    if not os.path.exists(CACHE_FILE):
        return False
    modified_time = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE))
    return datetime.now() - modified_time < timedelta(days=CACHE_EXPIRY_DAYS)

def load_cached_data():
    with open(CACHE_FILE, "r") as f:
        return json.load(f)

def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url)
    df = tables[0]
    return df["Symbol"].tolist()

def fetch_stock_data(tickers):
    stocks_data = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            if hist.empty:
                continue

            hist["daily_return"] = hist["Close"].pct_change()
            volatility = hist["daily_return"].std() * (252 ** 0.5)
            info = stock.info

            trend_data = hist.tail(10)
            trend = []
            for date_idx, row in trend_data.iterrows():
                trend.append({
                    "date": date_idx.strftime('%Y-%m-%d'),
                    "price": float(row["Close"])
                })
            
            # Get current price from info
            current_price = info.get("regularMarketPrice") or info.get("currentPrice")
            if current_price is None:
                current_price = hist["Close"].iloc[-1]
            current_price = round(float(current_price), 2)
            
            long_desc = info.get("longBusinessSummary", "")
            short_desc = (long_desc[:80] + "...") if len(long_desc) > 80 else long_desc

            stocks_data.append({
                "ticker": ticker,
                "company": info.get("longName", "N/A"),
                "sector": info.get("sector", "N/A").lower().strip(),
                "volatility": volatility,
                "beta": info.get("beta", 1.0),
                "trend": trend,
                "current_price": current_price,
                "short_desc": short_desc
            })
        except Exception as e:
            print(f"Error processing {ticker}: {e}", file=sys.stderr)
            continue
    return stocks_data

def classify_risk(stock):
    vol = stock["volatility"]
    beta = stock["beta"]
    if vol < 0.22:
        if beta < 0.90:
            return "minimal risk"
        elif beta <= 1.2:
            return "medium risk"
    elif vol <= 0.35:
        if 0.85 <= beta <= 1.2:
            return "medium risk"
    return "high risk"

def get_stock_data(force_refresh=False):
    if not force_refresh and is_cache_valid():
        return load_cached_data()
    else:
        if force_refresh and os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
        tickers = get_sp500_tickers()
        stock_data = fetch_stock_data(tickers)
        save_cache(stock_data)
        return stock_data

def recommend_stocks(risk_level, selected_sectors, force_refresh=False):
    risk_level = risk_level.lower()
    if risk_level not in ["minimal risk", "medium risk", "high risk"]:
        print(json.dumps({"error": "Invalid risk level. Choose from 'minimal risk', 'medium risk', or 'high risk'."}), flush=True)
        return

    SECTOR_ALIASES = {
        "finance": "financial services",
        "financials": "financial services",
        "banking": "financial services",
        "insurance": "financial services",
        "investment": "financial services",
        "investment firms": "financial services",
        "semiconductors": "technology",
        "ai": "technology",
        "artificial intelligence": "technology",
        "cybersecurity": "technology",
        "aerospace": "industrials",
        "defense": "industrials",
        "aviation": "industrials",
        "real estate": "real estate",
        "healthcare": "healthcare",
        "biotech": "healthcare",
        "pharmaceuticals": "healthcare",
        "energy": "energy",
        "utilities": "utilities",
        "technology": "technology",
        "materials": "basic materials",
        "commodities": "basic materials",
        "agriculture": "basic materials",
        "consumer goods": "consumer defensive",
        "consumer staples": "consumer defensive",
        "consumer discretionary": "consumer cyclical",
        "retail": "consumer cyclical",
        "automotive": "consumer cyclical",
        "entertainment": "communication services",
        "media": "communication services",
        "telecom": "communication services",
        "telecommunications": "communication services",
        "communication": "communication services"
    }

    TRUE_SEMI_TICKERS = {"NVDA", "AMD", "AVGO", "INTC", "TXN", "MU", "AMAT", "ADI", "QCOM", "ON", "LSCC", "KLAC", "NXPI", "TER"}
    TRUE_PHARMA_TICKERS = {"PFE", "JNJ", "MRK", "LLY", "BMY", "AMGN", "AZN", "GSK", "ZTS"}
    TRUE_BIOTECH_TICKERS = {"BIIB", "REGN", "VRTX", "GILD", "ILMN", "NBIX", "ALNY"}
    TRUE_AERO_TICKERS = {"LMT", "RTX", "NOC", "GD", "BA", "TDG", "TXT", "HII"}
    TRUE_AGRI_TICKERS = {"DE", "ADM", "MOS", "CF", "CTVA", "NTR"}

    stock_data = get_stock_data(force_refresh=force_refresh)
    for stock in stock_data:
        stock["risk"] = classify_risk(stock)

    final_recommendations = []
    for label in selected_sectors:
        label_lower = label.lower()
        mapped_sector = SECTOR_ALIASES.get(label_lower, label_lower)
        sector_matches = [s for s in stock_data if s["sector"] == mapped_sector and s["risk"] == risk_level]
        if label_lower == "semiconductors":
            sector_matches = [s for s in sector_matches if s["ticker"] in TRUE_SEMI_TICKERS]
        elif label_lower == "pharmaceuticals":
            sector_matches = [s for s in sector_matches if s["ticker"] in TRUE_PHARMA_TICKERS]
        elif label_lower == "biotech":
            sector_matches = [s for s in sector_matches if s["ticker"] in TRUE_BIOTECH_TICKERS]
        elif label_lower == "aerospace & defense":
            sector_matches = [s for s in sector_matches if s["ticker"] in TRUE_AERO_TICKERS]
        elif label_lower == "agriculture":
            sector_matches = [s for s in sector_matches if s["ticker"] in TRUE_AGRI_TICKERS]
        
        sector_matches.sort(key=lambda x: x["volatility"])
        sampled = sector_matches[:MAX_PER_SECTOR]
        for pick in sampled:
            if "source_sectors" not in pick:
                pick["source_sectors"] = [label_lower]
            elif label_lower not in pick["source_sectors"]:
                pick["source_sectors"].append(label_lower)
        final_recommendations.extend(sampled)

    if not final_recommendations:
        print(json.dumps({"error": "No suitable stocks found for your criteria."}), flush=True)
        return

    if len(final_recommendations) > MAX_TOTAL_RECOMMENDATIONS:
        final_recommendations = random.sample(final_recommendations, MAX_TOTAL_RECOMMENDATIONS)

    unique_dict = {}
    for s in final_recommendations:
        t = s["ticker"]
        if t not in unique_dict:
            unique_dict[t] = {
                "ticker": s["ticker"],
                "company": s["company"],
                "risk": s["risk"],
                "source_sectors": list(set(s.get("source_sectors", []))),
                "trend": s.get("trend", []),
                "current_price": s.get("current_price", 0.0),
                "short_desc": s.get("short_desc", "")
            }
        else:
            unique_dict[t]["source_sectors"] = list(set(unique_dict[t]["source_sectors"] + s.get("source_sectors", [])))
    final_list = list(unique_dict.values())
    print(json.dumps(final_list), flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--risk-level', required=True, type=str, help='Risk level (minimal risk, medium risk, high risk)')
    parser.add_argument('--sectors', required=True, type=str, help='Comma-separated list of sectors')
    parser.add_argument('--force-refresh', action='store_true', help='Force fetching fresh data and ignore the cache')
    args = parser.parse_args()
    recommend_stocks(
        args.risk_level,
        [s.strip() for s in args.sectors.split(",") if s.strip()],
        force_refresh=args.force_refresh
    )

if __name__ == "__main__":
    main()
