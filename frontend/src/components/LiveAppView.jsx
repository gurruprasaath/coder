import React, { useState, useEffect } from 'react';

import Renderer from './Renderer';
import ErrorBoundary from './ErrorBoundary';

export default function LiveAppView() {
  const searchParams = new URLSearchParams(window.location.search);
  let sessionId = searchParams.get('sessionId');
  
  if (sessionId) {
    localStorage.setItem('last_launched_session', sessionId);
  } else {
    sessionId = localStorage.getItem('last_launched_session');
  }

  const [config, setConfig] = useState(null);
  const [currentRole, setCurrentRole] = useState('Public');
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!sessionId) {
      setError("No session ID provided. Please generate an app from the Builder first.");
      return;
    }

    const savedConfig = localStorage.getItem(`config_${sessionId}`);
    if (!savedConfig) {
      setError(`No configuration found for session "${sessionId}". It may have expired or been cleared.`);
      return;
    }

    try {
      const parsed = JSON.parse(savedConfig);
      // Validate that the config actually has renderable content
      if (!parsed || !parsed.ui || !parsed.ui.pages || parsed.ui.pages.length === 0) {
        setError("Configuration is incomplete — no UI pages found. Please regenerate the app.");
        return;
      }
      setConfig(parsed);
    } catch (err) {
      setError("Failed to parse configuration. The stored data may be corrupted.");
    }
    
    const savedRole = localStorage.getItem(`role_${sessionId}`);
    if (savedRole) {
      setCurrentRole(savedRole);
    }
  }, [sessionId]);

  if (error) {
    return (
      <div style={{ backgroundColor: '#0f111a', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'Inter', system-ui, sans-serif" }}>
        <div style={{ padding: '40px', backgroundColor: '#161925', borderRadius: '12px', border: '1px solid #2a2e3d', maxWidth: '500px', textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: '16px' }}>🚫</div>
          <h2 style={{ color: '#f44336', fontSize: '1.3rem', marginBottom: '12px' }}>Live App Unavailable</h2>
          <p style={{ color: '#a6accd', fontSize: '0.9rem', lineHeight: 1.6, marginBottom: '24px' }}>{error}</p>
          <a 
            href="/" 
            style={{ display: 'inline-block', padding: '10px 24px', backgroundColor: '#646cff', color: '#fff', textDecoration: 'none', borderRadius: '8px', fontWeight: 600, fontSize: '0.9rem' }}
          >
            ← Go to Builder
          </a>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div style={{ backgroundColor: '#0f111a', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#a6accd', fontFamily: "'Inter', system-ui, sans-serif" }}>
        <div style={{ textAlign: 'center' }}>
          <div className="pulse-ring" style={{ width: '40px', height: '40px', margin: '0 auto 16px', borderColor: '#646cff' }}></div>
          <p>Loading application...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ height: '100vh', width: '100vw', backgroundColor: '#0f111a', margin: 0, padding: 0 }}>
      <ErrorBoundary>
        <Renderer 
          config={config} 
          currentRole={currentRole} 
          setCurrentRole={setCurrentRole} 
          runtimeId={sessionId} 
        />
      </ErrorBoundary>
    </div>
  );
}
