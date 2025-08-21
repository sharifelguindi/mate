# MATE Frontend

This directory contains the frontend assets for the MATE project, managed by Vite.

## Stack

- **Vite** - Modern frontend build tool with HMR
- **HTMX** - HTML-driven interactions without complex JavaScript
- **Alpine.js** - Lightweight reactive framework for UI components
- **Bootstrap 5** - CSS framework (imported via Vite)

## Development

Frontend assets are automatically compiled by the Vite container when running:

```bash
docker-compose -f docker-compose.local.yml up
```

The Vite dev server runs on http://localhost:3000 and provides:
- Hot Module Replacement (HMR)
- Fast builds
- Modern JavaScript support

## Structure

```
frontend/
├── src/
│   ├── main.js           # Main entry point
│   ├── styles/
│   │   └── main.css      # Main stylesheet
│   └── components/       # Alpine.js components
├── package.json
└── vite.config.js
```

## Adding New Features

### HTMX Example
```html
<button hx-get="/api/data" hx-target="#result">
  Load Data
</button>
<div id="result"></div>
```

### Alpine.js Example
```html
<div x-data="{ open: false }">
  <button @click="open = !open">Toggle</button>
  <div x-show="open" x-transition>
    Content here
  </div>
</div>
```

### Adding React/Vue Islands (Future)

When you need complex interactivity (like Cornerstone.js):

1. Install React/Vue: `npm install react react-dom @vitejs/plugin-react`
2. Update `vite.config.js` to include React plugin
3. Create island component in `src/islands/`
4. Mount to specific div in Django template

## Production Build

```bash
npm run build
```

This creates optimized assets in `mate/static/vite/` with:
- Minified code
- Content hashing
- Tree shaking
- Optimized chunks

## Notes

- CSS is bundled with JavaScript for optimal loading
- Bootstrap is imported through Vite instead of CDN
- CSRF tokens are automatically added to HTMX requests
- All assets go through Vite for consistency