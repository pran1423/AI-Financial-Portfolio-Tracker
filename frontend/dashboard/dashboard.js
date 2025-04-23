
const whiskerAreaPlugin = {
  id: 'whiskerAreaPlugin',
  afterDatasetsDraw(chart) {
    const { ctx, data, scales: { x, y } } = chart;
    const mainDataset = data.datasets[0]; // median line dataset
    if (!mainDataset || !mainDataset.predictions) return;

    const idxs = [2, 3, 4]; // only 1M, 3M, 6M
    const highPts = [], lowPts = [];

    idxs.forEach(i => {
      const p = mainDataset.predictions[i];
      if (!p) return;
      const xPos = x.getPixelForValue(chart.data.labels[i]);
      highPts.push({ x: xPos, y: y.getPixelForValue(parseFloat(p.high)) });
      lowPts.unshift({ x: xPos, y: y.getPixelForValue(parseFloat(p.low)) });
    });
    if (highPts.length < 3 || lowPts.length < 3) return;

    ctx.save();
    ctx.fillStyle = 'rgba(255, 215, 0, 0.3)';
    ctx.strokeStyle = 'gold';
    ctx.lineWidth = 1;
    ctx.beginPath();
    highPts.forEach((pt, i) => i ? ctx.lineTo(pt.x, pt.y) : ctx.moveTo(pt.x, pt.y));
    lowPts.forEach(pt => ctx.lineTo(pt.x, pt.y));
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    ctx.restore();
  }
};

let chart;              
let investmentsList = [];

// load user's investments
async function loadUserInvestments() {
  const email = localStorage.getItem('userEmail');
  if (!email) return console.log("No user email found.");
  document.getElementById('chartLoading').style.display = 'flex';
  document.getElementById('tableLoading').style.display = 'block';

  try {
    const resp = await fetch(`http://localhost:3000/api/user/investments?email=${email}`);
    const { investments } = await resp.json();
    if (!investments || !investments.length) return console.log("No investments.");
    investmentsList = investments;
    populateInvestmentTabs(investments);
    updateChart(investments[0].ticker);
    updatePortfolioTable(investments);
  } catch (err) {
    console.error(err);
  }
}

// create ticker tabs
function populateInvestmentTabs(invs) {
  const tabs = document.querySelector('.tabs');
  tabs.innerHTML = '';
  const tickers = [...new Set(invs.map(i => i.ticker.toUpperCase()))];
  tickers.forEach(t => {
    const d = document.createElement('div');
    d.className = 'tab';
    d.innerText = t;
    d.onclick = () => updateChart(t);
    tabs.appendChild(d);
  });
}

// fetch live price
async function getLivePrice(ticker) {
  try {
    const res = await fetch(`http://localhost:3000/api/user/current-price?ticker=${ticker}`);
    const { currentPrice } = await res.json();
    return currentPrice;
  } catch {
    return null;
  }
}

// update the Chart.js graph
async function updateChart(ticker) {
  document.getElementById('chartLoading').style.display = 'flex';
  try {
    const inv = investmentsList.find(i => i.ticker.toUpperCase() === ticker.toUpperCase());
    if (!inv) return console.error("No inv for", ticker);
    const buyPrice = parseFloat(inv.sharePrice);
    const livePrice = await getLivePrice(ticker);

    // fetch predictions
    const pRes = await fetch(`http://localhost:3000/api/predictions?ticker=${ticker}`);
    const pData = await pRes.json();
    const P = pData.predictions ||
      { "1M": pData["1M"], "3M": pData["3M"], "6M": pData["6M"] };

    const rd = v => parseFloat(v).toFixed(2);

    const labels = ["Buy Price", "Today", "1M", "3M", "6M"];
    const med = [
      parseFloat(rd(buyPrice)),
      parseFloat(rd(livePrice)),
      parseFloat(rd(P["1M"].median)),
      parseFloat(rd(P["3M"].median)),
      parseFloat(rd(P["6M"].median))
    ];
    const preds = {
      2: { high: rd(P["1M"].high), low: rd(P["1M"].low) },
      3: { high: rd(P["3M"].high), low: rd(P["3M"].low) },
      4: { high: rd(P["6M"].high), low: rd(P["6M"].low) }
    };

    // median dataset
    const medianDS = {
      label: ticker.toUpperCase(),
      data: med,
      borderColor: '#A38F5D',
      backgroundColor: 'rgba(163,143,93,0.2)',
      tension: 0.4,
      pointRadius: [4,4,4,4,4],
      pointBackgroundColor: '#A38F5D',
      predictions: preds
    };

    // high/low point datasets 
    const highDS = {
      label: 'High (Predicted)',
      data: [null,null,parseFloat(preds[2].high),parseFloat(preds[3].high),parseFloat(preds[4].high)],
      borderColor: 'gold',
      backgroundColor: 'gold',
      showLine: false,
      pointRadius: [0,0,5,5,5],
      pointStyle: 'circle'
    };
    const lowDS = {
      label: 'Low (Predicted)',
      data: [null,null,parseFloat(preds[2].low),parseFloat(preds[3].low),parseFloat(preds[4].low)],
      borderColor: 'gold',
      backgroundColor: 'gold',
      showLine: false,
      pointRadius: [0,0,5,5,5],
      pointStyle: 'circle'
    };

    
    const cfg = {
      type: 'line',
      data: { labels, datasets: [medianDS, highDS, lowDS] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { ticks: { color: 'white' }, title: { display: true, text: 'Time Period', color:'white' } },
          y: { ticks: { color: 'white' }, title: { display: true, text: 'Price ($)', color:'white' } }
        },
        plugins: {
          title: { display: true, text: `${ticker.toUpperCase()} Price & Predictions`, color:'white' },
          legend: { labels: { color:'white' } },
          tooltip: {
            callbacks: {
              label: ctx => `${ctx.dataset.label}: $${parseFloat(ctx.parsed.y).toFixed(2)}`
            }
          }
        }
      },
      plugins: [whiskerAreaPlugin]
    };

    if (!chart) {
      const ctx = document.getElementById('stockChart').getContext('2d');
      chart = new Chart(ctx, cfg);
    } else {
      chart.config.data = cfg.data;
      chart.config.options = cfg.options;
      chart.update();
    }
  } catch (err) {
    console.error(err);
  } finally {
    document.getElementById('chartLoading').style.display = 'none';
  }
}

async function updatePortfolioTable(investments) {
  const tbody = document.getElementById('portfolio-body');
  tbody.innerHTML = '';
  for (const inv of investments) {
    const t = inv.ticker.toUpperCase();
    const shares = inv.shares;
    const initial = (shares * inv.sharePrice).toFixed(2);
    const live = await getLivePrice(t);
    const todayVal = live ? (shares * live).toFixed(2) : 'N/A';

    let p1='N/A', p3='N/A', p6='N/A';
    try {
      const pr = await fetch(`http://localhost:3000/api/predictions?ticker=${t}`);
      const { predictions, "1M":a,"3M":b,"6M":c } = await pr.json();
      const P = predictions || {"1M":a,"3M":b,"6M":c};
      if (P["1M"]) p1 = `$${(shares*P["1M"].median).toFixed(2)}`;
      if (P["3M"]) p3 = `$${(shares*P["3M"].median).toFixed(2)}`;
      if (P["6M"]) p6 = `$${(shares*P["6M"].median).toFixed(2)}`;
    } catch {}
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${t}</td>
      <td>${shares}</td>
      <td>$${initial}</td>
      <td>$${todayVal}</td>
      <td>${p1}</td>
      <td>${p3}</td>
      <td>${p6}</td>
    `;
    tbody.appendChild(row);
  }
  document.getElementById('tableLoading').style.display = 'none';
}

window.addEventListener('DOMContentLoaded', loadUserInvestments);
