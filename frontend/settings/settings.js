
let selectedStocks   = [];  
let editingStockIdx  = null;
let tickerOptions    = [];
let selectedSectors  = [];
let selectedRisk     = null;

const tickerInput    = document.getElementById("stock-input");
const suggestionsBox = document.getElementById("stock-suggestions");
const dateInput      = document.getElementById("investment-date");
const sharesInput    = document.getElementById("share-amount");
const priceInput     = document.getElementById("share-price");
const stockList      = document.getElementById("selected-stocks");
const sectorSelect   = document.getElementById("sector-select");
const sectorsBox     = document.getElementById("selected-sectors");
const riskSelect     = document.getElementById("risk-select");
const riskBox        = document.getElementById("selected-risk");

window.addEventListener("DOMContentLoaded", async () => {
  // cap date to today
  const today = new Date().toISOString().split("T")[0];
  dateInput.setAttribute("max", today);

  // fetch all tickers
  try {
    const res = await fetch("http://localhost:3000/api/tickers");
    const data = await res.json();
    tickerOptions = data.tickers || [];
  } catch (err) {
    console.error("Could not load tickers:", err);
  }

  // load user’s saved settings
  const email = localStorage.getItem("userEmail");
  if (!email) return;

  // investments
  try {
    const invRes = await fetch(`http://localhost:3000/api/user/investments?email=${email}`);
    const invData = await invRes.json();
    selectedStocks = invData.investments.map(i => ({
      symbol: i.ticker,
      datePurchased: i.datePurchased.slice(0,10),
      shares: i.shares,
      sharePrice: i.sharePrice
    }));
  } catch(e){ console.error(e) }

  //preferences + risk
  try {
    const prefRes = await fetch(`http://localhost:3000/api/user/get?email=${email}`);
    const prefData = await prefRes.json();
    selectedSectors = prefData.user.investmentPreferences || [];
    selectedRisk    = prefData.user.riskTolerance || null;
  } catch(e){ console.error(e) }

  renderStocks();
  renderSectors();
  renderRisk();
});

tickerInput.addEventListener("input", () => {
  const val = tickerInput.value.toUpperCase().trim();
  suggestionsBox.innerHTML = "";
  if (!val) return suggestionsBox.classList.add("hidden");

  const matches = tickerOptions.filter(t=>t.startsWith(val)).slice(0,50);
  if (!matches.length) return suggestionsBox.classList.add("hidden");

  matches.forEach(t => {
    const div = document.createElement("div");
    div.textContent = t;
    div.addEventListener("click", () => {
      tickerInput.value = t;
      suggestionsBox.classList.add("hidden");
      suggestionsBox.innerHTML = "";
      tryFetchPrice();
    });
    suggestionsBox.appendChild(div);
  });
  suggestionsBox.classList.remove("hidden");
});

// hide suggestions on outside click
document.addEventListener("click", e => {
  if (!tickerInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
    suggestionsBox.classList.add("hidden");
  }
});

//  AUTO‐FETCH price when date or ticker changes
dateInput.addEventListener("change", () => {
  priceInput.value = "";
  tryFetchPrice();
});
tickerInput.addEventListener("blur", tryFetchPrice);

async function tryFetchPrice() {
  const sym = tickerInput.value.trim().toUpperCase();
  const dt  = dateInput.value;
  if (!sym||!dt||priceInput.value) return;
  try {
    const r = await fetch(`http://localhost:3000/api/user/historical-price?ticker=${sym}&date=${dt}`);
    const j = await r.json();
    if (j.price!=null) priceInput.value = j.price.toFixed(2);
  } catch(err){ console.error(err) }
}

//  Add / Edit stock
async function saveStock() {
  const sym = tickerInput.value.trim().toUpperCase();
  const dt  = dateInput.value;
  const sh  = parseFloat(sharesInput.value);
  const pr  = parseFloat(priceInput.value);

  if (!sym || !dt || isNaN(sh)||sh<=0 || isNaN(pr)||pr<=0) {
    return alert("Please fill in all fields with valid values.");
  }

  const record = { symbol: sym, datePurchased: dt, shares: sh, sharePrice: pr };
  if (editingStockIdx !== null) {
    selectedStocks[editingStockIdx] = record;
    editingStockIdx = null;
  } else {
    if (selectedStocks.some(s=>s.symbol===sym && s.datePurchased===dt)) {
      return alert("This investment is already listed.");
    }
    selectedStocks.push(record);
  }

  renderStocks();
  resetStockForm();

  suggestionsBox.classList.add("hidden");
  suggestionsBox.innerHTML = "";
}

// render stock list
function renderStocks(){
  stockList.innerHTML = "";
  selectedStocks.forEach((st,i)=>{
    const chip = document.createElement("div");
    chip.className = "sector-chip";
    chip.innerHTML = `
      ${st.symbol} on ${st.datePurchased} · ${st.shares} @ $${st.sharePrice.toFixed(2)}
      <span onclick="editStock(${i})">✎</span>
      <span onclick="removeStock(${i})">×</span>
    `;
    stockList.appendChild(chip);
  });
}

function editStock(i){
  const st = selectedStocks[i];
  tickerInput.value  = st.symbol;
  dateInput.value    = st.datePurchased;
  sharesInput.value  = st.shares;
  priceInput.value   = st.sharePrice;
  editingStockIdx    = i;
}
function removeStock(i){
  selectedStocks.splice(i,1);
  renderStocks();
}
function resetStockForm(){
  [tickerInput,dateInput,sharesInput,priceInput].forEach(x=>x.value="");
}

function renderSectors(){
  sectorsBox.innerHTML = "";
  selectedSectors.forEach(s=>{
    const chip = document.createElement("div");
    chip.className = "sector-chip";
    chip.innerHTML = `${s} <span onclick="removeSector('${s}')">×</span>`;
    sectorsBox.appendChild(chip);
  });
}
function addSector(){
  const s = sectorSelect.value;
  if (s && !selectedSectors.includes(s)) {
    selectedSectors.push(s);
    renderSectors();
  }
  sectorSelect.selectedIndex = 0;
}
function addSectorFromButton(s){
  if (s && !selectedSectors.includes(s)) {
    selectedSectors.push(s);
    renderSectors();
  }
}
function removeSector(s){
  selectedSectors = selectedSectors.filter(x=>x!==s);
  renderSectors();
}

// Risk
function renderRisk(){
  riskBox.innerHTML = "";
  if (selectedRisk) {
    const chip = document.createElement("div");
    chip.className = "sector-chip";
    chip.innerHTML = `${selectedRisk} <span onclick="removeRisk()">×</span>`;
    riskBox.appendChild(chip);
  }
}
function addRisk(){
  const r = riskSelect.value;
  if (r) {
    selectedRisk = r;
    renderRisk();
  }
}
function removeRisk(){
  selectedRisk = null;
  renderRisk();
}

// SAVE ALL to backend
async function saveAll(){
  const email = localStorage.getItem("userEmail");
  if (!email) return alert("Please log in.");

  try {
    await fetch("http://localhost:3000/api/user/invest-info", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify({
        email,
        investments: selectedStocks.map(s=>({
          ticker: s.symbol,
          datePurchased: s.datePurchased,
          shares: s.shares,
          sharePrice: s.sharePrice
        }))
      })
    });
    await fetch("http://localhost:3000/api/user/investment-preferences", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ email, preferences: selectedSectors })
    });
    await fetch("http://localhost:3000/api/user/risk-tolerance", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ email, riskTolerance: selectedRisk })
    });

    const banner = document.createElement("div");
    banner.textContent = "Settings saved successfully!";
    banner.style.cssText = "position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#A38F5D;color:#000;padding:12px 24px;border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,0.5);z-index:1000;";
    document.body.appendChild(banner);
    setTimeout(()=>banner.remove(), 3000);

  } catch(err){
    console.error(err);
    const banner = document.createElement("div");
    banner.textContent = "Error saving settings.";
    banner.style.cssText = "position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#D32F2F;color:#fff;padding:12px 24px;border-radius:6px;z-index:1000;";
    document.body.appendChild(banner);
    setTimeout(()=>banner.remove(), 3000);
  }
}
