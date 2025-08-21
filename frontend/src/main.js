// Main entry point for frontend assets
import './styles/main.css'
import htmx from 'htmx.org'
import Alpine from 'alpinejs'

// Initialize HTMX
window.htmx = htmx

// Initialize Alpine.js
window.Alpine = Alpine
Alpine.start()

// Import components
import './components/example-component.js'

// Log to confirm everything is working
console.log('MATE frontend loaded with HTMX and Alpine.js')

// Example: Add CSRF token to HTMX requests for Django
document.body.addEventListener('htmx:configRequest', (event) => {
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
  if (csrfToken) {
    event.detail.headers['X-CSRFToken'] = csrfToken
  }
})
