document.getElementById('createAccountForm').addEventListener('submit', function(event) {
    event.preventDefault(); // Prevent the default form submission

    // Perform form validation and account creation logic here

    // Redirect to the terms and conditions page after account creation
    window.location.href = '../Terms and conditions/terms-cond.html';
});
