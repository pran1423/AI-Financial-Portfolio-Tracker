import os
import torch
import requests
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from yahooquery import Ticker

def fetch_news(api_key, query, num_articles=10):
    """
    Fetches the latest news articles based on a given query (stock symbol or sector).
    """
    api_key = "39cebbeca2da487f9bb266eef4b907b6"
    url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&language=en&pageSize={num_articles}&apiKey={api_key}"
    response = requests.get(url)
    if response.status_code != 200:
        print("Error fetching news:", response.json())
        return []
    articles = response.json().get("articles", [])
    return [article["title"] + " " + article["description"] for article in articles if article["description"]]

def get_stock_sector(stock_symbol):
    """
    Fetches the sector for a given stock symbol using yahooquery (no API key needed).
    """
    try:
        stock = Ticker(stock_symbol)
        sector = stock.asset_profile.get(stock_symbol, {}).get("sector")
        if sector:
            return sector.lower()  # Standardize sector name
        else:
            print(f"Sector not found for {stock_symbol}.")
            return None
    except Exception as e:
        print(f"Error fetching sector for {stock_symbol}: {e}")
        return None

def segment_text(text, tokenizer, max_length=512):
    """
    Splits the input text into segments each with up to max_length tokens.
    """
    token_ids = tokenizer.encode(text, add_special_tokens=True)
    segments = []
    for i in range(0, len(token_ids), max_length):
        segment_ids = token_ids[i:i+max_length]
        segment_text = tokenizer.decode(segment_ids, skip_special_tokens=True)
        segments.append(segment_text)
    return segments

def analyze_sentiment(articles, tokenizer, model, device):
    """
    Runs sentiment analysis on fetched articles and calculates overall sentiment.
    """
    classifier = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer, device=device)
    total_score = 0.0
    sentiments = []
    
    for article in articles:
        segments = segment_text(article, tokenizer)
        for seg in segments:
            result = classifier(seg)[0]
            label = result["label"].lower()
            score_val = result["score"]
            sentiments.append((label, score_val))
            if label == "positive":
                total_score += score_val
            elif label == "negative":
                total_score -= score_val
    
    overall_sentiment = "Neutral"
    if total_score > 0:
        overall_sentiment = "Positive"
    elif total_score < 0:
        overall_sentiment = "Negative"
    
    return sentiments, overall_sentiment, total_score

def main():
    api_key = os.getenv("NEWS_API_KEY")  
    stock_symbol = input("Enter stock symbol (e.g., AAPL, TSLA): ").strip().upper()
    
    # Load FinBERT model and tokenizer
    model_name = "ProsusAI/finbert"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    
    # Use GPU if available
    device = 0 if torch.cuda.is_available() else -1
    print("Using GPU" if device == 0 else "Using CPU")
    
    # Get news articles for stock symbol and if not then sector. If none then just skip.
    articles = fetch_news(api_key, stock_symbol)
    if not articles:
        sector = get_stock_sector(stock_symbol)
        if sector:
            print(f"No news articles found for {stock_symbol}. Checking sector news: {sector}")
            articles = fetch_news(api_key, sector)
    
    if not articles:
        print(f"No news articles found for {stock_symbol} or its sector. Sentiment analysis skipped.")
        return
    
    # Run sentiment analysis
    sentiments, overall_sentiment, total_score = analyze_sentiment(articles, tokenizer, model, device)
    
    # Output results
    print("\nSentiment Analysis Results:")
    print("-----------------------------")
    for i, (label, score_val) in enumerate(sentiments, start=1):
        print(f"Article {i}: {label.capitalize()} (score: {score_val:.4f})")
    print("-----------------------------")
    print(f"Overall sentiment for {stock_symbol}: {overall_sentiment} (aggregated score: {total_score:.4f})")

if __name__ == "__main__":
    main()
