import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import LandingPage from './pages/Landing.tsx'
import AdminDashboard from './pages/AdminDashboard.tsx'
import { AuthProvider } from './contexts/AuthContext'

// Simple routing based on pathname
function Router() {
  const pathname = window.location.pathname;
  
  if (pathname === '/landing' || pathname === '/home') {
    return <LandingPage />;
  }
  
  if (pathname === '/admin' || pathname === '/admin/leiloeiros') {
    return <AdminDashboard />;
  }
  
  return <App />;
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <Router />
    </AuthProvider>
  </StrictMode>,
)
