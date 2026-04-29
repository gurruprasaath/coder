import React, { useState, useEffect } from 'react';

import { MemoryRouter } from 'react-router-dom';
import Renderer from './Renderer';
import ErrorBoundary from './ErrorBoundary';

export default function LiveAppView() {
  const searchParams = new URLSearchParams(window.location.search);
  const sessionId = searchParams.get('sessionId');
  const [config, setConfig] = useState(null);
  const [currentRole, setCurrentRole] = useState('Public');
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!sessionId) {
      setError("No session ID provided.");
      return;
    }

    const savedConfig = localStorage.getItem(`config_${sessionId}`);
    if (savedConfig) {
      try {
        setConfig(JSON.parse(savedConfig));
      } catch (err) {
        setError("Failed to parse configuration for this session.");
      }
    } else {
      setError("Session expired or configuration not found.");
    }
    
    const savedRole = localStorage.getItem(`role_${sessionId}`);
    if (savedRole) {
      setCurrentRole(savedRole);
    }
  }, [sessionId]);

  if (error) {
    return (
      <div style={{ padding: '50px', color: '#f44336', textAlign: 'center', backgroundColor: '#0f111a', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ padding: '30px', backgroundColor: '#1a1d27', borderRadius: '8px', border: '1px solid #2a2e3d' }}>
          <h2>Live App Error</h2>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div style={{ padding: '50px', textAlign: 'center', backgroundColor: '#0f111a', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#a6accd' }}>
        <div className="pulse-ring"></div>
        <p>Loading application...</p>
      </div>
    );
  }

  // The Renderer takes up the full screen now
  return (
    <div style={{ height: '100vh', width: '100vw', backgroundColor: '#0f111a', margin: 0, padding: 0 }}>
      <ErrorBoundary>
        <MemoryRouter>
          <Renderer 
            config={config} 
            currentRole={currentRole} 
            setCurrentRole={setCurrentRole} 
            runtimeId={sessionId} 
          />
        </MemoryRouter>
      </ErrorBoundary>
    </div>
  );
}
