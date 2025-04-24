
let investments   = [];
let editingIndex  = null;
let tickerOptions = [];


const tickerInput     = document.getElementById("ticker");
const suggestionsBox  = document.getElementById("ticker-suggestions");
const dateInput       = document.getElementById("purchase-date");
const sharesInput     = document.getElementById("total-invested");
const priceInput      = document.getElementById("share-price");
const investmentBtn   = document.getElementById("investment-btn");
const investmentList  = document.getElementById("investment-display");

window.addEventListener("DOMContentLoaded", () => {
  // cap date to today
  const today = new Date().toISOString().split("T")[0];
  dateInput.setAttribute("max", today);

  // fetch valid tickers from backend
  fetch("/api/tickers")
    .then(r => r.json())
    .then(data => { tickerOptions = data.tickers || []; })
    .catch(err => console.error("Could not load tickers:", err));
});


tickerInput.addEventListener("input", () => {
  const val = tickerInput.value.toUpperCase().trim();
  suggestionsBox.innerHTML = "";
  if (!val) { suggestionsBox.classList.add("hidden"); return; }

  const matches = tickerOptions.filter(t => t.startsWith(val)).slice(0, 50);
  if (!matches.length) { suggestionsBox.classList.add("hidden"); return; }

  matches.forEach(t => {
    const div = document.createElement("div");
    div.textContent = t;
    div.addEventListener("click", () => {
      tickerInput.value = t;
      suggestionsBox.classList.add("hidden");
      tryFetchPrice(); // immediately try auto‑fetch if date set
    });
    suggestionsBox.appendChild(div);
  });
  suggestionsBox.classList.remove("hidden");
});


document.addEventListener("click", e => {
  if (!tickerInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
    suggestionsBox.classList.add("hidden");
  }
});

// Auto‑fetch historical price when ticker OR date changes
dateInput.addEventListener("change", () => {
  priceInput.value = ""; // clear old
  tryFetchPrice();
});
tickerInput.addEventListener("blur", tryFetchPrice);

function tryFetchPrice() {
  const ticker = tickerInput.value.trim().toUpperCase();
  const date   = dateInput.value;
  if (!ticker || !date || priceInput.value) return;

  fetch(`/api/user/historical-price?ticker=${ticker}&date=${date}`)
    .then(r => r.json())
    .then(json => {
      if (json.price != null) priceInput.value = json.price.toFixed(2);
    })
    .catch(err => console.error("Error fetching historical price:", err));
}

// Add or Update Investment
function addOrUpdateInvestment() {
  document.querySelectorAll(".error-message").forEach(el => el.remove());
  document.querySelectorAll(".input-error").forEach(el => el.classList.remove("input-error"));

  let valid = true;
  const today = new Date().toISOString().split("T")[0];
  function showError(el, msg) {
    const p = document.createElement("p");
    p.className = "error-message";
    p.innerText = msg;
    el.classList.add("input-error");
    el.parentNode.appendChild(p);
    valid = false;
  }

  const ticker = tickerInput.value.trim().toUpperCase();
  const date   = dateInput.value;
  const shares = parseFloat(sharesInput.value);
  const price  = parseFloat(priceInput.value);

  if (!ticker)                    showError(tickerInput,    "Ticker required.");
  if (!date || date > today)      showError(dateInput,      date > today ? "Future date?" : "Valid date required.");
  if (isNaN(shares) || shares<=0) showError(sharesInput,    "Enter a positive share count.");
  if (isNaN(price)  || price<=0)  showError(priceInput,     "Enter a positive share price.");

  if (!valid) return;

  const record = { ticker, datePurchased: date, shares, sharePrice: price };

  if (editingIndex !== null) {
    investments[editingIndex] = record;
    editingIndex = null;
    investmentBtn.textContent = "Add Investment";
  } else {
    if (investments.length >= 5) {
      showError(sharesInput, "Max 5 investments allowed.");
      return;
    }
    investments.push(record);
  }

  renderInvestmentList();
  resetForm();
}

// Render the list
function renderInvestmentList() {
  investmentList.innerHTML = "";
  investments.forEach((inv, i) => {
    const li = document.createElement("li");
    li.className = "investment-item";
    li.innerHTML = `
      <span class="investment-ticker">${inv.ticker}</span>
      <span>${inv.shares} @ $${inv.sharePrice.toFixed(2)}</span>
      <button class="edit-btn"   onclick="editInvestment(${i})">Edit</button>
      <button class="remove-btn" onclick="removeInvestment(${i})">✖</button>
    `;
    investmentList.appendChild(li);
  });
}

function resetForm() {
  [tickerInput, dateInput, sharesInput, priceInput].forEach(i => i.value = "");
}
function editInvestment(i) {
  const inv = investments[i];
  tickerInput.value   = inv.ticker;
  dateInput.value     = inv.datePurchased;
  sharesInput.value   = inv.shares;
  priceInput.value    = inv.sharePrice;
  editingIndex        = i;
  investmentBtn.textContent = "Update Investment";
}
function removeInvestment(i) {
  investments.splice(i,1);
  renderInvestmentList();
}

function checkAndNavigate(){
  if (!investments.length) {
    document.getElementById("continue-error").classList.remove("hidden");
    return;
  }

  // grab the logged‑in email
  const email = localStorage.getItem('userEmail') || 'test@example.com';

  // POST to your backend
  fetch('/api/user/invest-info', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, investments })
  })
  .then(r => r.json())
  .then(json => {
    if (json.error) {
      alert("Error saving investments: " + json.error);
    } else {

      window.location.href = "../Risk_Tolerance/RiskTolerance.html";
    }
  })
  .catch(err => {
    console.error("Failed to save investments:", err);
    alert("Network error, please try again.");
  });
}

function openTooltip()  {
  document.getElementById("tooltip-modal" ).style.display = "block";
  document.getElementById("modal-overlay").style.display = "block";
}
function closeTooltip() {
  document.getElementById("tooltip-modal" ).style.display = "none";
  document.getElementById("modal-overlay").style.display = "none";
}
