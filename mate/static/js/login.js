// Login page functionality

document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    
    if (loginForm) {
        // Add loading state to form submission
        loginForm.addEventListener('submit', function(e) {
            const button = this.querySelector('.btn-primary');
            if (button) {
                button.classList.add('loading');
                button.disabled = true;
            }
        });
    }
    
    // Auto-remove any error messages after 5 seconds
    const alerts = document.querySelectorAll('.alert-danger');
    if (alerts.length > 0) {
        setTimeout(function() {
            alerts.forEach(function(alert) {
                alert.style.transition = 'opacity 0.5s ease';
                alert.style.opacity = '0';
                setTimeout(function() {
                    alert.remove();
                }, 500);
            });
        }, 5000);
    }
    
    // Focus on first input field
    const firstInput = document.querySelector('.form-control');
    if (firstInput) {
        firstInput.focus();
    }
    
    // Add enter key support for form submission
    const inputs = document.querySelectorAll('.form-control');
    inputs.forEach(function(input, index) {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && index === inputs.length - 1) {
                loginForm.submit();
            }
        });
    });
});