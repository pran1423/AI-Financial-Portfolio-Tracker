document.getElementById('loginForm').addEventListener('submit', async function(event) {
  event.preventDefault();

  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  const errorMessage = document.getElementById('error-message');

  try {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await response.json();
    console.log('Login response:', data);
    if (response.ok) {
      // Save the user's email 
      localStorage.setItem('userEmail', email);
      // Redirect to the dashboard
      window.location.href = "../dashboard/dashboard.html";
    } else {
      errorMessage.textContent = data.error || 'Invalid email or password.';
      errorMessage.style.display = "block";
    }
  } catch (error) {
    console.error('Error during login:', error);
    errorMessage.textContent = 'Something went wrong. Please try again.';
    errorMessage.style.display = "block";
  }
});

document.getElementById("email").addEventListener("input", () => {
  document.getElementById("error-message").style.display = "none";
});
document.getElementById("password").addEventListener("input", () => {
  document.getElementById("error-message").style.display = "none";
});
