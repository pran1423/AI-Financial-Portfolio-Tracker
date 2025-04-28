import os
import sys
import torch
import requests
import json
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from yahooquery import Ticker
from datetime import datetime, timedelta

# Configuration
NEWSAPI_KEY = "39cebbeca2da487f9bb266eef4b907b6"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SENTIMENT_CACHE_DIR = os.path.join(DATA_DIR, "sentiment_cache")
SENTIMENT_CACHE_EXPIRY_DAYS = 7
os.makedirs(SENTIMENT_CACHE_DIR, exist_ok=True)

# Caching utilities

def get_cached_sentiment(ticker):
    cache_path = os.path.join(SENTIMENT_CACHE_DIR, f"{ticker}_sentiment.json")
    if not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, "r") as f:
            data = json.load(f)
            timestamp = datetime.fromisoformat(data.get("timestamp"))
            if datetime.now() - timestamp > timedelta(days=SENTIMENT_CACHE_EXPIRY_DAYS):
                return None
            return data
    except Exception as e:
        print(f"Error reading sentiment cache for {ticker}: {e}", file=sys.stderr)
        return None


def save_cached_sentiment(ticker, overall_sentiment, total_score, articles):
    cache_path = os.path.join(SENTIMENT_CACHE_DIR, f"{ticker}_sentiment.json")
    data = {
        "timestamp": datetime.now().isoformat(),
        "overall_sentiment": overall_sentiment,
        "total_score": total_score,
        "articles": articles
    }
    with open(cache_path, "w") as f:
        json.dump(data, f, indent=4)

# Helper functions

def get_stock_name(symbol):
    try:
        prof = Ticker(symbol).asset_profile.get(symbol, {})
        return prof.get("longName") or symbol
    except Exception:
        return symbol


def get_stock_sector(symbol):
    try:
        prof = Ticker(symbol).asset_profile.get(symbol, {})
        return prof.get("sector", None)
    except Exception as e:
        print(f"Error fetching sector for {symbol}: {e}", file=sys.stderr)
        return None


def fetch_news(query, num_articles=10):
    url = (
        f"https://newsapi.org/v2/everything"
        f"?qInTitle={requests.utils.quote(query)}"
        f"&sortBy=publishedAt"
        f"&language=en"
        f"&pageSize={num_articles}"
        f"&apiKey={NEWSAPI_KEY}"
    )
    resp = requests.get(url)
    if resp.status_code != 200:
        print("Error fetching news:", resp.json(), file=sys.stderr)
        return []
    raw = resp.json().get("articles", [])
    out = []
    for art in raw:
        title = art.get("title", "") or ""
        desc = art.get("description", "") or ""
        text = (title + " " + desc).lower()
        if query.lower() not in text:
            continue
        out.append({
            "title": title,
            "description": desc,
            "url": art.get("url", ""),
            "source": art.get("source", {}).get("name", "Unknown"),
            "publishedAt": art.get("publishedAt", "")
        })
    return out


def segment_text(text, tokenizer, max_length=512):
    token_ids = tokenizer.encode(text, add_special_tokens=True)
    segments = []
    for i in range(0, len(token_ids), max_length):
        seg_ids = token_ids[i:i+max_length]
        segments.append(tokenizer.decode(seg_ids, skip_special_tokens=True))
    return segments


def analyze_sentiment(articles, tokenizer, model, device):
    classifier = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer, device=device)
    total_score = 0.0
    for art in articles:
        text = (art["title"] or "") + " " + (art["description"] or "")
        score = 0.0
        for seg in segment_text(text, tokenizer):
            r = classifier(seg)[0]
            label = r["label"].lower()
            if label == "positive":
                score += r["score"]
            elif label == "negative":
                score -= r["score"]
        art["sentiment_label"] = "positive" if score > 0 else "negative" if score < 0 else "neutral"
        art["sentiment_score"] = round(score, 4)
        total_score += score
    overall = "Positive" if total_score > 0 else "Negative" if total_score < 0 else "Neutral"
    return articles, overall, round(total_score, 4)

# Main execution
def main():
    stock_symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    query = get_stock_name(stock_symbol)

    # Check cache
    cached = get_cached_sentiment(stock_symbol)
    if cached:
        print(json.dumps(cached, indent=4))
        return

    # Load model & tokenizer
    model_name = "ProsusAI/finbert"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    sys.stderr.write("Using GPU\n" if torch.cuda.is_available() else "Using CPU\n")

    # Fetch articles
    articles = fetch_news(query)
    if not articles:
        sector = get_stock_sector(stock_symbol)
        if sector:
            sys.stderr.write(f"No news for {stock_symbol}. Checking sector: {sector}\n")
            articles = fetch_news(sector)

    if not articles:
        print(json.dumps({"error": f"No news articles found for {stock_symbol} or its sector."}))
        sys.exit(1)

    # Analyze sentiment
    articles, overall_sentiment, total_score = analyze_sentiment(
        articles, tokenizer, model, 0 if torch.cuda.is_available() else -1
    )

    # Save cache & output
    save_cached_sentiment(stock_symbol, overall_sentiment, total_score, articles)
    result = {
        "query": query,
        "overall_sentiment": overall_sentiment,
        "total_score": total_score,
        "articles": articles
    }
    print(json.dumps(result, indent=4))

if __name__ == "__main__":
    main()
