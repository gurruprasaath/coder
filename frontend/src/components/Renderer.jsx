import React, { useState } from 'react';
import { Routes, Route, NavLink, Navigate, useLocation } from 'react-router-dom';
import FormRenderer from './FormRenderer';
import TableRenderer from './TableRenderer';
import ButtonRenderer from './ButtonRenderer';
import { isEndpointAllowed } from '../utils/auth';

// Derive a smart icon per page based on route/name keywords
function getPageIcon(page) {
  const name = (page.name || '').toLowerCase();
  const route = (page.route || '').toLowerCase();
  if (name.includes('dashboard') || route.includes('dashboard')) return '📊';
  if (name.includes('home') || route === '/' || route === '/home') return '🏠';
  if (name.includes('contact'))  return '👤';
  if (name.includes('user'))     return '👥';
  if (name.includes('product'))  return '📦';
  if (name.includes('order'))    return '🛒';
  if (name.includes('setting'))  return '⚙️';
  if (name.includes('report'))   return '📈';
  if (name.includes('task'))     return '✅';
  if (name.includes('message') || name.includes('chat'))  return '💬';
  if (name.includes('login') || name.includes('auth'))    return '🔐';
  if (name.includes('register') || name.includes('signup')) return '📝';
  return '📄';
}

export default function Renderer({ config, currentRole, setCurrentRole, runtimeId }) {
  const [lastAction, setLastAction] = useState('None');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const location = useLocation();

  if (!config) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', backgroundColor: '#0f111a', color: '#666', fontSize: '1.2rem' }}>
        No App Generated
      </div>
    );
  }

  const allPages = config.ui?.pages || [];
  const roles = config.auth?.roles || [];
  const appName = config.ui?.app_name || config.app_name || 'My App';

  const visiblePages = allPages; // Show all pages regardless of role

  // Current page name for the top bar breadcrumb
  const currentPage = visiblePages.find(p => {
    const route = p.route?.startsWith('/') ? p.route.slice(1) : p.route;
    return location.pathname.endsWith(route);
  });

  return (
    <div style={{ display: 'flex', height: '100vh', backgroundColor: '#0f111a', color: '#e0e0e0', fontFamily: "'Inter', system-ui, -apple-system, sans-serif" }}>

      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside style={{
        width: sidebarCollapsed ? '68px' : '250px',
        backgroundColor: '#0d0f15',
        borderRight: '1px solid #1e212b',
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.25s ease',
        overflow: 'hidden',
        flexShrink: 0,
      }}>
        {/* App Logo / Brand */}
        <div style={{
          padding: sidebarCollapsed ? '20px 0' : '20px',
          borderBottom: '1px solid #1e212b',
          display: 'flex',
          alignItems: 'center',
          justifyContent: sidebarCollapsed ? 'center' : 'space-between',
          minHeight: '68px',
        }}>
          {!sidebarCollapsed && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
              <div style={{
                width: '32px', height: '32px', borderRadius: '8px',
                background: 'linear-gradient(135deg, #646cff, #a164ff)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '1rem', fontWeight: 'bold', color: '#fff', flexShrink: 0
              }}>
                {appName.charAt(0).toUpperCase()}
              </div>
              <span style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', whiteSpace: 'nowrap' }}>{appName}</span>
            </div>
          )}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            style={{
              background: 'none', border: 'none', color: '#666', cursor: 'pointer',
              fontSize: '1.1rem', padding: '4px', flexShrink: 0
            }}
            title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {sidebarCollapsed ? '▸' : '◂'}
          </button>
        </div>

        {/* Navigation Links */}
        <nav style={{ display: 'flex', flexDirection: 'column', padding: '12px 8px', gap: '2px', flex: 1, overflowY: 'auto' }}>
          {visiblePages.length === 0 ? (
            !sidebarCollapsed && <div style={{ color: '#444', fontStyle: 'italic', padding: '10px', fontSize: '0.85rem' }}>No accessible pages</div>
          ) : (
            visiblePages.map((page, index) => {
              const relativeRoute = page.route?.startsWith('/') ? page.route.slice(1) : page.route;
              const icon = getPageIcon(page);
              return (
                <NavLink
                  key={index}
                  to={relativeRoute}
                  style={({ isActive }) => ({
                    padding: sidebarCollapsed ? '12px 0' : '10px 14px',
                    borderRadius: '8px',
                    textDecoration: 'none',
                    color: isActive ? '#fff' : '#8892b0',
                    backgroundColor: isActive ? 'rgba(100, 108, 255, 0.15)' : 'transparent',
                    fontWeight: isActive ? 600 : 400,
                    fontSize: '0.9rem',
                    transition: 'all 0.15s ease',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    justifyContent: sidebarCollapsed ? 'center' : 'flex-start',
                    borderLeft: isActive ? '3px solid #646cff' : '3px solid transparent',
                  })}
                  title={sidebarCollapsed ? page.name : undefined}
                >
                  <span style={{ fontSize: '1.1rem', flexShrink: 0 }}>{icon}</span>
                  {!sidebarCollapsed && <span>{page.name}</span>}
                </NavLink>
              );
            })
          )}
        </nav>

        {/* Sidebar Footer */}
        {!sidebarCollapsed && (
          <div style={{ padding: '15px', borderTop: '1px solid #1e212b', fontSize: '0.75rem', color: '#444' }}>
            Powered by AI Compiler
          </div>
        )}
      </aside>

      {/* ── Main Content Area ────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* ── Top Bar ──────────────────────────────────────────────────────── */}
        <header style={{
          padding: '0 28px',
          height: '56px',
          backgroundColor: '#12151e',
          borderBottom: '1px solid #1e212b',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexShrink: 0,
        }}>
          {/* Left: Breadcrumb */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.9rem' }}>
            <span style={{ color: '#555' }}>{appName}</span>
            <span style={{ color: '#333' }}>/</span>
            <span style={{ color: '#a6accd', fontWeight: 600 }}>{currentPage?.name || 'Page'}</span>
          </div>

          {/* Right: Role + Status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {/* Last API indicator */}
            <div style={{
              fontSize: '0.78rem', color: '#555', fontFamily: 'monospace',
              backgroundColor: 'rgba(0,0,0,0.3)', padding: '4px 10px',
              borderRadius: '4px', border: '1px solid #1e212b',
            }}>
              API: <span style={{ color: lastAction !== 'None' ? '#4caf50' : '#555' }}>{lastAction}</span>
            </div>

            {/* Role Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{
                width: '28px', height: '28px', borderRadius: '50%',
                background: 'linear-gradient(135deg, #646cff, #a164ff)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '0.75rem', color: '#fff', fontWeight: 700,
              }}>
                {(currentRole || 'P').charAt(0).toUpperCase()}
              </div>
              <select
                value={currentRole}
                onChange={(e) => {
                  setCurrentRole(e.target.value);
                  if (runtimeId) localStorage.setItem(`role_${runtimeId}`, e.target.value);
                }}
                style={{
                  padding: '6px 10px', borderRadius: '6px',
                  backgroundColor: '#1a1d27', color: '#e0e0e0',
                  border: '1px solid #2a2e3d', outline: 'none',
                  cursor: 'pointer', fontSize: '0.85rem',
                }}
              >
                {roles.length > 0 ? (
                  roles.map((role, i) => <option key={i} value={role}>{role}</option>)
                ) : (
                  <>
                    <option value="Admin">Admin</option>
                    <option value="User">User</option>
                    <option value="Public">Public</option>
                  </>
                )}
              </select>
            </div>
          </div>
        </header>

        {/* ── Page Content ──────────────────────────────────────────────── */}
        <main style={{ padding: '32px', flex: 1, overflowY: 'auto', backgroundColor: '#0f111a' }}>
          <Routes>
            {visiblePages.map((page, index) => {
              const path = page.route?.startsWith('/') ? page.route : `/${page.route}`;
              return (
                <Route key={index} path={path} element={
                  <div className="page-content" style={{ animation: 'fadeIn 0.3s ease' }}>
                    <h2 style={{
                      marginBottom: '28px', color: '#fff', fontSize: '1.6rem',
                      fontWeight: 700, paddingBottom: '14px',
                      borderBottom: '1px solid #1e212b',
                      display: 'flex', alignItems: 'center', gap: '12px'
                    }}>
                      <span>{getPageIcon(page)}</span> {page.name}
                    </h2>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
                      {page.components?.map((comp, cIndex) => {
                        const epRef = comp.endpoint_ref;
                        const allEndpoints = config.api?.endpoints || [];
                        const endpointExists = epRef && allEndpoints.some(ep => ep.id === epRef || ep.name === epRef);
                        const isAllowed = !epRef
                          ? true
                          : isEndpointAllowed(epRef, currentRole, config.auth?.rules || []);

                        let warningBadge = null;
                        if (!endpointExists) {
                          warningBadge = <span style={{ marginLeft: '10px', fontSize: '0.75rem', backgroundColor: '#ff9800', color: '#fff', padding: '2px 6px', borderRadius: '4px' }}>⚠️ Missing Endpoint</span>;
                        } else if (!isAllowed) {
                          warningBadge = <span style={{ marginLeft: '10px', fontSize: '0.75rem', backgroundColor: '#f44336', color: '#fff', padding: '2px 6px', borderRadius: '4px' }}>🔒 Access Denied</span>;
                        }

                        if (comp.type === 'form') {
                          return (
                            <div key={cIndex} style={{ position: 'relative' }}>
                              {warningBadge && <div style={{ position: 'absolute', top: '-10px', right: '10px', zIndex: 10 }}>{warningBadge}</div>}
                              <FormRenderer component={comp} config={config} runtimeId={runtimeId} onRoleChange={setCurrentRole} onAction={setLastAction} />
                            </div>
                          );
                        }
                        if (comp.type === 'table') {
                          return (
                            <div key={cIndex} style={{ position: 'relative' }}>
                              {warningBadge && <div style={{ position: 'absolute', top: '-10px', right: '10px', zIndex: 10 }}>{warningBadge}</div>}
                              <TableRenderer component={comp} config={config} runtimeId={runtimeId} onAction={setLastAction} />
                            </div>
                          );
                        }
                        if (comp.type === 'button') {
                          return (
                            <div key={cIndex} style={{ position: 'relative', display: 'inline-block' }}>
                              {warningBadge && <div style={{ position: 'absolute', top: '-20px', left: '0', whiteSpace: 'nowrap' }}>{warningBadge}</div>}
                              <ButtonRenderer component={comp} config={config} runtimeId={runtimeId} onAction={setLastAction} />
                            </div>
                          );
                        }
                        return (
                          <div key={cIndex} style={{ padding: '12px', border: '1px dashed #333', borderRadius: '8px', backgroundColor: '#151821' }}>
                            <strong>{comp.type}:</strong> {comp.name}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                } />
              );
            })}

            {visiblePages.length > 0 && (
              <Route path="*" element={
                <Navigate to={visiblePages[0].route?.startsWith('/') ? visiblePages[0].route.slice(1) : visiblePages[0].route} replace />
              } />
            )}
          </Routes>
        </main>
      </div>
    </div>
  );
}
