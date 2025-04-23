console.log('createAccount.js loaded');

document.getElementById('createAccountForm').addEventListener('submit', async function(event) {
  event.preventDefault();

  const email           = document.getElementById('email').value.trim();
  const password        = document.getElementById('password').value;
  const confirmPassword = document.getElementById('confirm-password').value;
  const feedbackEl      = document.getElementById('password-feedback');
  feedbackEl.textContent = "";  

  // basic match check
  if (password !== confirmPassword) {
    feedbackEl.textContent = "Passwords don’t match.";
    return;
  }

  // enforce stronger password: at least 8 chars, uppercase, lowercase, digit
  const lengthOk   = password.length >= 8;
  const upperOk    = /[A-Z]/.test(password);
  const lowerOk    = /[a-z]/.test(password);
  const digitOk    = /\d/.test(password);

  if (!lengthOk || !upperOk || !lowerOk || !digitOk) {
    let msgs = [];
    if (!lengthOk) msgs.push("at least 8 characters");
    if (!upperOk)  msgs.push("one uppercase letter");
    if (!lowerOk)  msgs.push("one lowercase letter");
    if (!digitOk)  msgs.push("one digit");
    feedbackEl.textContent = "Password must contain " + msgs.join(", ") + ".";
    return;
  }

  try {
    const response = await fetch('http://localhost:3000/api/auth/create-account', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, confirmPassword }),
    });
    const data = await response.json();
    console.log('Response from server:', data);

    if (response.ok) {
      // Save email for later steps
      localStorage.setItem('userEmail', email);

      const banner = document.createElement('div');
      banner.textContent = "Account created successfully!";
      banner.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: #A38F5D;
        color: #000;
        padding: 12px 24px;
        border-radius: 6px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.5);
        z-index: 1000;
      `;
      document.body.appendChild(banner);
      setTimeout(() => banner.remove(), 3000);

  
      setTimeout(() => {
        window.location.href = '../Terms_Conditions/terms-cond.html';
      }, 1200);

    } else {
      feedbackEl.textContent = data.error || "Error creating account.";
    }
  } catch (error) {
    console.error('Error:', error);
    feedbackEl.textContent = "Network error, please try again.";
  }
});
