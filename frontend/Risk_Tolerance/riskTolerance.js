
function navigateTo(page) {
  window.location.href = page;
}

document.querySelectorAll(".risk-btn").forEach(button => {
  button.addEventListener("click", async function() {
    // Remove the class from all buttons and add it to the clicked one
    document.querySelectorAll(".risk-btn").forEach(btn => btn.classList.remove("selected"));
    this.classList.add("selected");

    const riskLevel = this.textContent.trim();
    const email = localStorage.getItem('userEmail') || 'test@example.com';

    // Send the selected risk level to the backend
    try {
      const response = await fetch('/api/user/risk-tolerance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, riskTolerance: riskLevel })
      });
      const data = await response.json();
      if (response.ok) {
        console.log('Risk tolerance updated:', data);
      } else {
        alert(data.error || 'Error updating risk tolerance.');
      }
    } catch (error) {
      console.error('Error updating risk tolerance:', error);
    }
  });
});
