// Login page entry point
import './styles/login.css'

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

        // Re-enable button if form submission fails (browser validation)
        loginForm.addEventListener('invalid', function() {
            const button = this.querySelector('.btn-primary');
            if (button) {
                button.classList.remove('loading');
                button.disabled = false;
            }
        }, true);
    }

    // Auto-remove any error messages after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    if (alerts.length > 0) {
        setTimeout(function() {
            alerts.forEach(function(alert) {
                alert.style.transition = 'opacity 0.3s ease';
                alert.style.opacity = '0';
                setTimeout(function() {
                    alert.style.display = 'none';
                }, 300);
            });
        }, 5000);
    }

    // Focus on first input field if no errors
    const firstInput = document.querySelector('.form-input:not(.is-invalid)');
    if (firstInput && !document.querySelector('.alert')) {
        firstInput.focus();
    }
});
