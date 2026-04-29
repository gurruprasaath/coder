import React, { useState } from 'react';
import { handleAction } from '../services/runtimeEngine';

export default function ButtonRenderer({ component, config, runtimeId, onAction }) {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null); // { type: 'success' | 'error', text: '' }

  const handleClick = async () => {
    const endpoint = component.endpoint_ref || '';
    
    setLoading(true);
    setMessage(null);
    
    // Update debug panel state in parent if provided
    if (onAction) onAction(endpoint);

    try {
      // For buttons, we assume empty request body since there are no form inputs
      const response = await handleAction(endpoint, {}, config, runtimeId);

      if (response.success) {
        setMessage({ type: 'success', text: response.message || 'Action completed successfully' });
      } else {
        setMessage({ type: 'error', text: response.message || 'Action failed' });
      }
    } catch (err) {
      console.error('[ButtonRenderer] Error during click action:', err);
      setMessage({ type: 'error', text: 'An unexpected error occurred' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="component-container button-component" style={{ margin: '15px 0', display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <button 
        onClick={handleClick}
        disabled={loading}
        style={{
          padding: '12px 24px',
          backgroundColor: '#4caf50',
          color: '#fff',
          border: 'none',
          borderRadius: '4px',
          fontWeight: 'bold',
          cursor: loading ? 'not-allowed' : 'pointer',
          opacity: loading ? 0.7 : 1,
          alignSelf: 'flex-start',
          transition: 'background-color 0.2s',
          fontSize: '1rem'
        }}
        onMouseOver={(e) => { if (!loading) e.currentTarget.style.backgroundColor = '#45a049'; }}
        onMouseOut={(e) => { if (!loading) e.currentTarget.style.backgroundColor = '#4caf50'; }}
      >
        {loading ? 'Processing...' : component.name}
      </button>

      {message && (
        <div style={{
          padding: '10px',
          borderRadius: '4px',
          backgroundColor: message.type === 'success' ? 'rgba(76, 175, 80, 0.1)' : 'rgba(244, 67, 54, 0.1)',
          color: message.type === 'success' ? '#4caf50' : '#f44336',
          border: `1px solid ${message.type === 'success' ? '#4caf50' : '#f44336'}`,
          fontSize: '0.9rem',
          maxWidth: 'fit-content'
        }}>
          {message.text}
        </div>
      )}
    </div>
  );
}
