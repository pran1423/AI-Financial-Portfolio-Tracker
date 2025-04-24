import os
import sys
import torch
import requests
import json
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from yahooquery import Ticker

NEWSAPI_KEY = "39cebbeca2da487f9bb266eef4b907b6"

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
        desc  = art.get("description", "") or ""
        text = (title + " " + desc).lower()
        if query.lower() not in text:
            continue
        out.append({
            "title":       title,
            "description": desc,
            "url":         art.get("url",""),
            "source":      art.get("source",{}).get("name","Unknown"),
            "publishedAt": art.get("publishedAt","")
        })
    return out

def get_stock_name(symbol):
    """Fetch the official company name via yahooquery."""
    try:
        prof = Ticker(symbol).asset_profile.get(symbol, {})
        return prof.get("longName") or symbol
    except:
        return symbol

def segment_text(text, tokenizer, max_length=512):
    ids = tokenizer.encode(text, add_special_tokens=True)
    segs = []
    for i in range(0, len(ids), max_length):
        chunk = ids[i:i+max_length]
        segs.append(tokenizer.decode(chunk, skip_special_tokens=True))
    return segs

def analyze_sentiment(articles, tokenizer, model, device):
    classifier = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer, device=device)
    total_score = 0.0
    for art in articles:
        text = (art["title"] + " " + art["description"]).strip()
        score = 0.0
        for seg in segment_text(text, tokenizer):
            r = classifier(seg)[0]
            if r["label"].lower()=="positive":
                score += r["score"]
            elif r["label"].lower()=="negative":
                score -= r["score"]
        art["sentiment_label"] = "positive" if score>0 else "negative" if score<0 else "neutral"
        art["sentiment_score"] = round(score,4)
        total_score += score
    overall = "Positive" if total_score>0 else "Negative" if total_score<0 else "Neutral"
    return articles, overall, round(total_score,4)

def main():
    symbol = sys.argv[1] if len(sys.argv)>1 else "AAPL"
    query = get_stock_name(symbol)
    
    sys.stderr.write("Using GPU\n" if torch.cuda.is_available() else "Using CPU\n")
    tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
    model     = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")

    # fetch & filter
    arts = fetch_news(query, num_articles=10)
    if not arts:
        print(json.dumps({"error": f"No headlines found for {query}"}))
        sys.exit(0)

    # sentiment
    arts, overall, total = analyze_sentiment(arts, tokenizer, model, 0 if torch.cuda.is_available() else -1)
    print(json.dumps({
        "query": query,
        "overall_sentiment": overall,
        "total_score": total,
        "articles": arts
    }))

if __name__=="__main__":
    main()
