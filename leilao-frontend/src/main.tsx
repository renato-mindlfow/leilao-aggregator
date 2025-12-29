import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import LandingPage from './pages/Landing.tsx'

// Simple routing based on pathname
function Router() {
  const pathname = window.location.pathname;
  
  if (pathname === '/landing' || pathname === '/home') {
    return <LandingPage />;
  }
  
  return <App />;
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Router />
  </StrictMode>,
)
