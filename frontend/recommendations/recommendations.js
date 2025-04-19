async function loadRecommendations() {
  const sectionsContainer = document.getElementById("recommendations-sections");
  const email = localStorage.getItem('userEmail');
  if (!email) {
    sectionsContainer.innerHTML = "<p>Please log in to see recommendations.</p>";
    return;
  }

  sectionsContainer.innerHTML = "<p>Loading recommendations...</p>";

  try {
    const response = await fetch(`http://localhost:3000/api/recommendations?email=${encodeURIComponent(email)}`);
    const data = await response.json();

    if (data.error) {
      sectionsContainer.innerHTML = `<p>Error: ${data.error}</p>`;
      return;
    }

    // Group recommendations by sector
    let groups = {};
    data.forEach(rec => {
      if (!rec.source_sectors || rec.source_sectors.length === 0) {
        if (!groups["Other"]) groups["Other"] = [];
        groups["Other"].push(rec);
      } else {
        rec.source_sectors.forEach(sector => {
          const sectorKey = sector.charAt(0).toUpperCase() + sector.slice(1).replace(/[^a-zA-Z0-9]/g, '');
          if (!groups[sectorKey]) groups[sectorKey] = [];
          groups[sectorKey].push(rec);
        });
      }
    });

    sectionsContainer.innerHTML = "";

    for (let sector in groups) {
      const sectionDiv = document.createElement("div");
      sectionDiv.className = "section-group";
      const header = document.createElement("h2");
      header.textContent = sector;
      sectionDiv.appendChild(header);

      const cardsContainer = document.createElement("div");
      cardsContainer.className = "cards-container";

      groups[sector].forEach((rec, index) => {
        const card = document.createElement("div");
        card.className = "recommendation-card";

        const descHtml = rec.short_desc ? `<p class="stock-description">${rec.short_desc}</p>` : "";
        card.innerHTML = `
          <h3>${rec.ticker} - ${rec.company}</h3>
          ${descHtml}
          <p class="last-price">Last Price: $${rec.current_price}</p>
          <div class="chart-container">
            <canvas id="chart-${sector}-${index}"></canvas>
          </div>
        `;

        cardsContainer.appendChild(card);

        if (rec.trend && Array.isArray(rec.trend) && rec.trend.length > 0) {
          const labels = rec.trend.map(pt => pt.date);
          const dataPoints = rec.trend.map(pt => pt.price);

          const canvas = card.querySelector("canvas");
          if (canvas) {
            const ctx = canvas.getContext('2d');
            new Chart(ctx, {
              type: 'line',
              data: {
                labels: labels,
                datasets: [{
                  data: dataPoints,
                  borderColor: "#00c853", 
                  borderWidth: 2,
                  fill: false,
                  tension: 0.3
                }]
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { display: false },
                  tooltip: {
                    callbacks: {
                      label: function (context) {
                        const price = context.parsed.y;
                        return `$${price.toFixed(2)}`;
                      }
                    }
                  }
                },
                scales: {
                  x: {
                    display: true,
                    ticks: {
                      maxRotation: 90,
                      minRotation: 45
                    }
                  },
                  y: { display: false }
                }
              }
            });
          }
        }
      });

      sectionDiv.appendChild(cardsContainer);
      sectionsContainer.appendChild(sectionDiv);
    }
  } catch (error) {
    console.error("Error loading recommendations:", error);
    sectionsContainer.innerHTML = "<p>Error loading recommendations.</p>";
  }
}

window.onload = loadRecommendations;
