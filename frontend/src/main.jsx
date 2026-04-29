import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import LiveAppView from './components/LiveAppView.jsx'

const isLiveApp = window.location.pathname === '/app';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {isLiveApp ? (
      <LiveAppView />
    ) : (
      <BrowserRouter>
        <App />
      </BrowserRouter>
    )}
  </StrictMode>,
)
