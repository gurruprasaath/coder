import React, { useState, useEffect } from 'react';
import FormRenderer from './FormRenderer';
import TableRenderer from './TableRenderer';
import { isEndpointAllowed } from '../utils/auth';

export default function Renderer({ config, currentRole, setCurrentRole, runtimeId }) {
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [lastAction, setLastAction] = useState('None');

  // Reset to first page when a new config is received or role changes
  useEffect(() => {
    setCurrentPageIndex(0);
  }, [config, currentRole]);

  if (!config) {
    return (
      <div className="placeholder">
        [ App Preview Placeholder ]<br/>
        No App Generated
      </div>
    );
  }

  const allPages = config.ui?.pages || [];
  
  // Filter pages based on currentRole OR 'public' (defaulting to public if unspecified)
  const visiblePages = allPages.filter(page => {
    const requiredRole = (page.access_role || 'public').toLowerCase();
    const activeRole = (currentRole || '').toLowerCase();
    
    // Page is visible if it explicitly matches the user's role, or if it's designated as public
    return requiredRole === 'public' || requiredRole === activeRole;
  });

  return (
    <div className="renderer-container" style={{ display: 'flex', flexDirection: 'column', minHeight: '100%', padding: '16px', position: 'relative' }}>
      
      {/* Debug Panel */}
      <div style={{
        position: 'absolute',
        top: '10px',
        right: '10px',
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        color: '#00ff00',
        padding: '8px 12px',
        fontSize: '0.75rem',
        borderRadius: '6px',
        border: '1px solid #333',
        fontFamily: 'monospace',
        zIndex: 1000,
        pointerEvents: 'none'
      }}>
        <div style={{ marginBottom: '2px' }}><strong style={{ color: '#aaa' }}>ROLE:</strong> {currentRole}</div>
        <div style={{ marginBottom: '2px' }}><strong style={{ color: '#aaa' }}>PAGE:</strong> {visiblePages[currentPageIndex]?.name || 'None'}</div>
        <div><strong style={{ color: '#aaa' }}>LAST API:</strong> {lastAction}</div>
      </div>

      {/* Role Switcher */}
      <div style={{ display: 'flex', justifyContent: 'flex-start', padding: '10px 20px', backgroundColor: '#121212', borderBottom: '1px solid #2a2e3d' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <label style={{ color: '#a6accd', fontSize: '0.9rem' }}>Viewing as Role:</label>
          <select 
            value={currentRole} 
            onChange={(e) => {
              setCurrentRole(e.target.value);
              if (runtimeId) localStorage.setItem(`role_${runtimeId}`, e.target.value);
            }}
            style={{ padding: '6px 10px', borderRadius: '4px', backgroundColor: '#242936', color: '#fff', border: '1px solid #3b4252' }}
          >
            <option value="Admin">Admin</option>
            <option value="User">User</option>
            <option value="Public">Public</option>
          </select>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav style={{ display: 'flex', gap: '10px', padding: '15px 20px', borderBottom: '1px solid #2a2e3d', backgroundColor: '#1a1d27', flexWrap: 'wrap' }}>
        {visiblePages.length === 0 ? (
          <div style={{ color: '#666', fontStyle: 'italic' }}>No accessible pages</div>
        ) : (
          visiblePages.map((page, index) => (
            <button
              key={index}
              onClick={() => setCurrentPageIndex(index)}
              style={{
                padding: '8px 16px',
                borderRadius: '4px',
                border: 'none',
                backgroundColor: index === currentPageIndex ? '#646cff' : '#242936',
                color: index === currentPageIndex ? '#fff' : '#a6accd',
                cursor: 'pointer',
                fontWeight: index === currentPageIndex ? 'bold' : 'normal',
                transition: 'background-color 0.2s'
              }}
            >
              {page.name}
            </button>
          ))
        )}
      </nav>

      {/* Current Page Content */}
      <div className="page-content" style={{ padding: '20px 0', flex: 1 }}>
        {visiblePages.length > 0 && visiblePages[currentPageIndex] && (
          <>
            <h2 style={{ marginBottom: '20px', color: '#fff', fontSize: '1.4rem' }}>
              {visiblePages[currentPageIndex].name}
            </h2>
            
            <div className="components-list" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {visiblePages[currentPageIndex].components
                ?.map((comp, cIndex) => {
                  const isAllowed = isEndpointAllowed(comp.endpoint_ref, currentRole, config.auth?.rules || []);
                  
                  if (!isAllowed) {
                    return (
                      <div key={cIndex} style={{ padding: '20px', border: '1px dashed #f44336', margin: '15px 0', borderRadius: '8px', backgroundColor: 'rgba(244, 67, 54, 0.05)', color: '#f44336', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <h3 style={{ marginBottom: '5px' }}>{comp.name}</h3>
                          <span style={{ fontSize: '0.85rem', opacity: 0.8 }}>Access Denied: You do not have permission to view this component.</span>
                        </div>
                        <span style={{ fontSize: '1.5rem', opacity: 0.8 }}>🔒</span>
                      </div>
                    );
                  }

                  if (comp.type === 'form') {
                    return <FormRenderer key={cIndex} component={comp} config={config} runtimeId={runtimeId} onRoleChange={setCurrentRole} onAction={setLastAction} />;
                  }
                  if (comp.type === 'table') {
                    return <TableRenderer key={cIndex} component={comp} config={config} runtimeId={runtimeId} onAction={setLastAction} />;
                  }
                  return (
                    <div key={cIndex} style={{ padding: '10px', border: '1px dashed #444', margin: '10px 0', borderRadius: '4px', backgroundColor: '#242936' }}>
                      <strong>{comp.type}:</strong> {comp.name}
                    </div>
                  );
                })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
