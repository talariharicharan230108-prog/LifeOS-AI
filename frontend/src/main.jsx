import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// One-time clean complete reset of stale development/shared state (v5 = Complete Wipe)
const RESET_KEY = 'lifeos_clean_reset_v5';
if (!localStorage.getItem(RESET_KEY)) {
  // Clear everything — removes old shared keys, tokens, and data.
  localStorage.clear();
  sessionStorage.clear();
  
  localStorage.setItem(RESET_KEY, 'true');
  console.log('[LifeOS] Clean reset v5 applied — ALL stale data and tokens cleared.');
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
