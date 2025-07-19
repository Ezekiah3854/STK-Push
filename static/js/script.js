 // Set timeout to hide alert messages after a few seconds
 setTimeout(() => {
    const alertSuccess = document.getElementById("alert-success");
    const alertError = document.getElementById("alert-error");
    
    if (alertSuccess) {
      alertSuccess.style.display = "none";
    }
    
    if (alertError) {
      alertError.style.display = "none";
    }
  }, 5000); // Adjust this value for delay in milliseconds (5000ms = 5 seconds)

  // Clear form fields after submission
  const paymentForm = document.getElementById("paymentForm");
  paymentForm.addEventListener('submit', (event) => {
    setTimeout(() => {
      document.getElementById("phoneNo").value = '';
      document.getElementById("amount").value = '';
    }, 0);
  });