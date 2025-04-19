import os
import sys
import torch
import requests
import json
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from yahooquery import Ticker

def fetch_news(api_key, query, num_articles=10):
    api_key = "39cebbeca2da487f9bb266eef4b907b6"
    url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&language=en&pageSize={num_articles}&apiKey={api_key}"
    response = requests.get(url)
    if response.status_code != 200:
        print("Error fetching news:", response.json(), file=sys.stderr)
        return []
    articles = response.json().get("articles", [])
    articles_data = []
    for article in articles:
        source_name = article.get("source", {}).get("name", "Unknown")
        articles_data.append({
            "title": article.get("title", ""),
            "description": article.get("description", ""),
            "url": article.get("url", ""),
            "source": source_name,
            "publishedAt": article.get("publishedAt", "")
        })
    return articles_data

def get_stock_sector(stock_symbol):
    try:
        stock = Ticker(stock_symbol)
        sector = stock.asset_profile.get(stock_symbol, {}).get("sector")
        if sector:
            return sector.lower()
        else:
            print(f"Sector not found for {stock_symbol}.", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Error fetching sector for {stock_symbol}: {e}", file=sys.stderr)
        return None

def segment_text(text, tokenizer, max_length=512):
    token_ids = tokenizer.encode(text, add_special_tokens=True)
    segments = []
    for i in range(0, len(token_ids), max_length):
        segment_ids = token_ids[i:i+max_length]
        segment_text = tokenizer.decode(segment_ids, skip_special_tokens=True)
        segments.append(segment_text)
    return segments

def analyze_sentiment(articles, tokenizer, model, device):
    classifier = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer, device=device)
    total_score = 0.0
    for article in articles:
        # Use .get() to avoid NoneType issues
        text = (article.get("title") or "") + " " + (article.get("description") or "")
        segments = segment_text(text, tokenizer)
        article_score = 0.0
        for seg in segments:
            result = classifier(seg)[0]
            label = result["label"].lower()
            score_val = result["score"]
            if label == "positive":
                article_score += score_val
            elif label == "negative":
                article_score -= score_val
        if article_score > 0:
            article_label = "positive"
        elif article_score < 0:
            article_label = "negative"
        else:
            article_label = "neutral"
        article["sentiment_label"] = article_label
        article["sentiment_score"] = round(article_score, 4)
        total_score += article_score
    overall_sentiment = "Neutral"
    if total_score > 0:
        overall_sentiment = "Positive"
    elif total_score < 0:
        overall_sentiment = "Negative"
    return articles, overall_sentiment, total_score

def main():
    stock_symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    model_name = "ProsusAI/finbert"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    
    # Instead of printing to stdout, send this to stderr
    sys.stderr.write("Using GPU\n" if torch.cuda.is_available() else "Using CPU\n")
    
    articles = fetch_news("", stock_symbol)
    if not articles:
        sector = get_stock_sector(stock_symbol)
        if sector:
            sys.stderr.write(f"No news articles found for {stock_symbol}. Checking sector news: {sector}\n")
            articles = fetch_news("", sector)
    if not articles:
        print(json.dumps({"error": f"No news articles found for {stock_symbol} or its sector."}))
        sys.exit()

    articles, overall_sentiment, total_score = analyze_sentiment(articles, tokenizer, model, 0 if torch.cuda.is_available() else -1)
    result = {
         "articles": articles,
         "overall_sentiment": overall_sentiment,
         "total_score": round(total_score, 4)
    }
    print(json.dumps(result))

if __name__ == "__main__":
    main()
