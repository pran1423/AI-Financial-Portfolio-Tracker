let selectedSectors = [];
const maxSelections = 5;

const banner         = document.getElementById("prefBanner");
const selectedContainer = document.getElementById("selected-sectors");
const sectorDropdown = document.getElementById("sector-dropdown");
const addSectorBtn   = document.getElementById("add-sector-btn");
const sectorButtons  = document.querySelectorAll(".sector-btn");


function showBanner(message, isError = false) {
  banner.textContent = message;
  banner.style.backgroundColor = isError ? "#5c0f0f" : "#163c28";
  banner.style.borderColor     = isError ? "#a14f4f" : "#2fa14f";
  banner.classList.add("show");
  setTimeout(() => banner.classList.remove("show"), 3000);
}


function updateSelectedSectors() {
  selectedContainer.innerHTML = "";
  selectedSectors.forEach(sector => {
    const tag = document.createElement("div");
    tag.classList.add("selected-sector");
    tag.innerHTML = `
      ${sector}
      <button class="remove-btn" onclick="removeSector('${sector}')">✖</button>
    `;
    selectedContainer.appendChild(tag);
  });

  // disable when max reached
  const full = selectedSectors.length >= maxSelections;
  addSectorBtn.disabled = full;
  sectorDropdown.disabled = full;
  sectorButtons.forEach(btn => {
    btn.disabled = full && !selectedSectors.includes(btn.dataset.sector);
  });
}

// adds from dropdown 
addSectorBtn.addEventListener("click", () => {
  const val = sectorDropdown.value;
  if (val && !selectedSectors.includes(val) && selectedSectors.length < maxSelections) {
    selectedSectors.push(val);
    // remove that option so they can't pick again
    const opt = sectorDropdown.querySelector(`option[value="${val}"]`);
    if (opt) opt.remove();
    updateSelectedSectors();
  }
});

// adds from quick‐buttons
sectorButtons.forEach(btn => {
  btn.addEventListener("click", () => {
    const s = btn.dataset.sector;
    if (!selectedSectors.includes(s) && selectedSectors.length < maxSelections) {
      selectedSectors.push(s);
      btn.style.display = "none";
      updateSelectedSectors();
    }
  });
});

function removeSector(sector) {
  selectedSectors = selectedSectors.filter(s => s !== sector);
  // restore dropdown option
  let exists = Array.from(sectorDropdown.options).some(o => o.value === sector);
  if (!exists) {
    const newOpt = document.createElement("option");
    newOpt.value = sector;
    newOpt.innerText = sector;
    sectorDropdown.appendChild(newOpt);
  }
  const btn = document.querySelector(`.sector-btn[data-sector="${sector}"]`);
  if (btn) btn.style.display = "inline-block";

  updateSelectedSectors();
}

function navigateTo(url) {
  window.location.href = url;
}

async function submitPreferences() {
  const email = localStorage.getItem('userEmail');
  if (!email) {
    showBanner("No account found. Please create one first.", true);
    return;
  }

  try {
    const res = await fetch('/api/user/investment-preferences', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, preferences: selectedSectors })
    });
    const data = await res.json();

    if (res.ok) {
      showBanner("✅ Preferences saved successfully!");
      // redirect after a short pause
      setTimeout(() => window.location.href = "../dashboard/dashboard.html", 1500);
    } else {
      showBanner("❌ " + (data.error || "Could not save preferences."), true);
    }
  } catch (err) {
    console.error(err);
    showBanner("❌ Network error. Please try again.", true);
  }
}


updateSelectedSectors();
