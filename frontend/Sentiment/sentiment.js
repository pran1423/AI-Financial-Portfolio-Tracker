function toggleAccordion(button) {
  const content = button.nextElementSibling;
  content.style.display = (content.style.display === "block") ? "none" : "block";
}

// load sentiment for a given ticker and update its card
function loadSentimentForTicker(stockSymbol, cardElement) {
  const contentArea = cardElement.querySelector('.accordion-content');
  contentArea.innerHTML = "<p>Loading sentiment...</p>";

  fetch(`http://localhost:3000/api/sentiment?stock=${stockSymbol}`)
    .then(response => response.json())
    .then(data => {
      contentArea.innerHTML = "";

      const tickerSentimentSpan = cardElement.querySelector('.ticker-sentiment');
      if (data.error) {
        tickerSentimentSpan.textContent = data.error;
        return;
      }
      tickerSentimentSpan.textContent = data.overall_sentiment;
      
      const overallSpan = document.getElementById('overall-sentiment');
      const timestampSpan = document.getElementById('timestamp');
      if (!overallSpan.dataset.updated) {
        overallSpan.innerHTML = `${data.overall_sentiment} (<span>${data.total_score.toFixed(2)}</span>)`;
        timestampSpan.textContent = new Date().toLocaleTimeString();
        const sentimentLower = data.overall_sentiment.toLowerCase();
        if (sentimentLower === "positive") {
          overallSpan.style.color = "#00C26E";
          tickerSentimentSpan.style.color = "#00C26E";
        } else if (sentimentLower === "negative") {
          overallSpan.style.color = "#FF4F4F";
          tickerSentimentSpan.style.color = "#FF4F4F";
        } else {
          overallSpan.style.color = "#FFA500";
          tickerSentimentSpan.style.color = "#FFA500";
        }
        overallSpan.dataset.updated = "true";
      }

      // Create article cards
      data.articles.forEach((article) => {
        const articleDiv = document.createElement('div');
        articleDiv.className = 'article-card';

        // Title as clickable link
        const h3 = document.createElement('h3');
        const link = document.createElement('a');
        link.href = article.url || '#';
        link.target = '_blank';
        link.textContent = article.title || 'No Title';
        h3.appendChild(link);
        articleDiv.appendChild(h3);

        const barDiv = document.createElement('div');
        barDiv.className = 'bar';
        if (article.sentiment_label === 'positive') {
          barDiv.classList.add('positive-bar');
        } else if (article.sentiment_label === 'negative') {
          barDiv.classList.add('negative-bar');
        } else {
          barDiv.classList.add('neutral-bar');
        }
        const widthPercent = Math.min(Math.abs(article.sentiment_score) * 20, 100);
        barDiv.style.width = `${widthPercent}%`;
        articleDiv.appendChild(barDiv);

        // Article description
        const summaryP = document.createElement('p');
        summaryP.className = 'summary';
        summaryP.textContent = article.description || 'No description available.';
        articleDiv.appendChild(summaryP);

        // source and published time
        const metaP = document.createElement('p');
        metaP.className = 'meta';
        const sourceName = article.source || 'Unknown Source';
        const publishedTime = article.publishedAt ? new Date(article.publishedAt).toLocaleString() : 'N/A';
        metaP.textContent = `${sourceName} • ${publishedTime}`;
        articleDiv.appendChild(metaP);

        contentArea.appendChild(articleDiv);
      });
    })
    .catch(err => {
      console.error('Error loading sentiment:', err);
      cardElement.querySelector('.accordion-content').innerHTML = "<p>Error loading sentiment.</p>";
    });
}

// Load sentiment cards from the database 
function loadSentimentsForInvestments() {
  const container = document.getElementById('sentiment-cards-container');
  container.innerHTML = "<p style='color: #fff;'>Loading portfolio investments...</p>"; 

  const email = localStorage.getItem('userEmail');
  if (!email) {
    container.innerHTML = "<p style='color: #fff;'>No user email found. Please log in.</p>";
    return;
  }
  
  fetch(`http://localhost:3000/api/user/investments?email=${email}`)
    .then(response => response.json())
    .then(data => {
      container.innerHTML = ""; 
      if (data.error) {
        container.innerHTML = `<p style="color: #fff;">Error: ${data.error}</p>`;
        return;
      }
      const investments = data.investments || [];
      if (!Array.isArray(investments) || investments.length === 0) {
        container.innerHTML = "<p style='color: #fff;'>No portfolio investments loaded. Please add investments from your portfolio.</p>";
        return;
      }
      const tickers = [...new Set(investments.map(inv => inv.ticker.toUpperCase()))];
      tickers.forEach(ticker => {
        const card = createSentimentCard(ticker);
        container.appendChild(card);
        loadSentimentForTicker(ticker, card);
      });
    })
    .catch(err => {
      console.error("Error fetching investments:", err);
      container.innerHTML = "<p style='color: #fff;'>Error loading portfolio investments.</p>";
    });
}

function createSentimentCard(ticker) {
  const card = document.createElement('section');
  card.className = 'stock-card';

  const headerButton = document.createElement('button');
  headerButton.className = 'accordion-header';
  headerButton.innerHTML = `<span class="stock-symbol">${ticker}</span> — <span class="ticker-sentiment">N/A</span>`;
  headerButton.onclick = () => toggleAccordion(headerButton);
  card.appendChild(headerButton);

  const contentDiv = document.createElement('div');
  contentDiv.className = 'accordion-content';
  card.appendChild(contentDiv);

  return card;
}

function loadSentimentFromInput() {
  const input = document.getElementById('tickerInput').value.trim().toUpperCase();
  if (!input) {
    alert('Please enter a ticker symbol.');
    return;
  }
  document.getElementById('tickerInput').value = "";
  
  const container = document.getElementById('sentiment-cards-container');
  // Check if a card for this ticker already exists
  const existingCard = Array.from(container.getElementsByClassName('stock-card'))
    .find(card => card.querySelector('.stock-symbol').textContent === input);
  if (existingCard) {
    loadSentimentForTicker(input, existingCard);
  } else {
    const card = createSentimentCard(input);
    container.appendChild(card);
    loadSentimentForTicker(input, card);
  }
}

// load sentiment cards for user investments
function initSentimentPage() {
  loadSentimentsForInvestments();
}

document.addEventListener("DOMContentLoaded", initSentimentPage);
