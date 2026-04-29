import React, { useState, useEffect } from 'react';
import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import FormRenderer from './FormRenderer';
import TableRenderer from './TableRenderer';
import ButtonRenderer from './ButtonRenderer';
import { isEndpointAllowed } from '../utils/auth';

export default function Renderer({ config, currentRole, setCurrentRole, runtimeId }) {
  const [lastAction, setLastAction] = useState('None');

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
    <div className="renderer-container" style={{ display: 'flex', minHeight: '100%', position: 'relative', backgroundColor: '#1a1d27', color: '#fff', borderRadius: '8px', overflow: 'hidden', border: '1px solid #2a2e3d' }}>
      
      {/* Sidebar Navigation */}
      <aside style={{ width: '250px', backgroundColor: '#121212', borderRight: '1px solid #2a2e3d', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '20px', borderBottom: '1px solid #2a2e3d' }}>
          <h2 style={{ fontSize: '1.2rem', margin: 0, color: '#646cff', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '1.5rem' }}>⬡</span>
            Acme Corp App
          </h2>
        </div>
        <nav style={{ display: 'flex', flexDirection: 'column', padding: '15px 10px', gap: '5px' }}>
          {visiblePages.length === 0 ? (
            <div style={{ color: '#666', fontStyle: 'italic', padding: '10px' }}>No accessible pages</div>
          ) : (
            visiblePages.map((page, index) => {
              // Ensure route has a leading slash
              const path = page.route?.startsWith('/') ? page.route : `/${page.route}`;
              return (
                <NavLink
                  key={index}
                  to={path}
                  style={({ isActive }) => ({
                    padding: '12px 15px',
                    borderRadius: '6px',
                    textDecoration: 'none',
                    color: isActive ? '#fff' : '#a6accd',
                    backgroundColor: isActive ? '#646cff' : 'transparent',
                    fontWeight: isActive ? 'bold' : 'normal',
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px'
                  })}
                >
                  {({ isActive }) => (
                    <>
                      <span style={{ opacity: isActive ? 1 : 0.5 }}>{index % 2 === 0 ? '📄' : '📊'}</span>
                      {page.name}
                    </>
                  )}
                </NavLink>
              )
            })
          )}
        </nav>
      </aside>

      {/* Main Content Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative', overflowY: 'auto' }}>
        
        {/* Topbar */}
        <header style={{ padding: '15px 25px', backgroundColor: '#1e212b', borderBottom: '1px solid #2a2e3d', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
            <label style={{ color: '#a6accd', fontSize: '0.9rem', fontWeight: 'bold' }}>Role Context:</label>
            <select 
              value={currentRole} 
              onChange={(e) => {
                setCurrentRole(e.target.value);
                if (runtimeId) localStorage.setItem(`role_${runtimeId}`, e.target.value);
              }}
              style={{ padding: '8px 12px', borderRadius: '4px', backgroundColor: '#242936', color: '#fff', border: '1px solid #3b4252', outline: 'none', cursor: 'pointer' }}
            >
              <option value="Admin">Admin</option>
              <option value="User">User</option>
              <option value="Public">Public</option>
            </select>
          </div>

          <div style={{ fontSize: '0.85rem', color: '#a6accd', fontFamily: 'monospace', backgroundColor: 'rgba(0,0,0,0.3)', padding: '6px 12px', borderRadius: '4px', border: '1px solid #2a2e3d' }}>
            LAST API: <span style={{ color: '#00ff00' }}>{lastAction}</span>
          </div>
        </header>

        {/* Page Content Area via Routing */}
        <main style={{ padding: '30px', flex: 1 }}>
          <Routes>
            {visiblePages.map((page, index) => {
              const path = page.route?.startsWith('/') ? page.route : `/${page.route}`;
              return (
                <Route key={index} path={path} element={
                  <div className="page-content animation-fade-in">
                    <h2 style={{ marginBottom: '25px', color: '#fff', fontSize: '1.8rem', borderBottom: '1px solid #2a2e3d', paddingBottom: '15px' }}>
                      {page.name}
                    </h2>
                    
                    <div className="components-list" style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
                      {page.components?.map((comp, cIndex) => {
                        const isAllowed = isEndpointAllowed(comp.endpoint_ref, currentRole, config.auth?.rules || []);
                        
                        if (!isAllowed) {
                          return (
                            <div key={cIndex} style={{ padding: '20px', border: '1px dashed #f44336', borderRadius: '8px', backgroundColor: 'rgba(244, 67, 54, 0.05)', color: '#f44336', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
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
                        if (comp.type === 'button') {
                          return <ButtonRenderer key={cIndex} component={comp} config={config} runtimeId={runtimeId} onAction={setLastAction} />;
                        }
                        return (
                          <div key={cIndex} style={{ padding: '10px', border: '1px dashed #444', margin: '10px 0', borderRadius: '4px', backgroundColor: '#242936' }}>
                            <strong>{comp.type}:</strong> {comp.name}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                } />
              )
            })}
            
            {/* Fallback route - automatically redirect to the first available page if route is not found */}
            {visiblePages.length > 0 && (
              <Route path="*" element={
                <Navigate to={visiblePages[0].route?.startsWith('/') ? visiblePages[0].route : `/${visiblePages[0].route}`} replace />
              } />
            )}
          </Routes>
        </main>
      </div>
    </div>
  );
}
