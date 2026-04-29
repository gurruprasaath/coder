import React, { useState } from 'react';
import { handleAction } from '../services/runtimeEngine';

export default function FormRenderer({ component, config, runtimeId, onRoleChange, onAction }) {
  const [values, setValues] = useState({});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null); // { type: 'success' | 'error', text: '' }

  const handleChange = (field, value) => {
    setValues(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const endpoint = component.endpoint_ref || '';
    
    setLoading(true);
    setMessage(null);
    
    // Update debug panel state
    if (onAction) onAction(endpoint);

    try {
      // Call runtime engine with endpoint, form values, and global config
      const response = await handleAction(endpoint, values, config, runtimeId);

      if (response.success) {
        setMessage({ type: 'success', text: response.message || 'Action completed successfully' });
        setValues({}); // Clear form on success
        
        // Update global role if engine returned one
        if (response.role && onRoleChange) {
          onRoleChange(response.role);
        }
      } else {
        setMessage({ type: 'error', text: response.message || 'Action failed' });
      }
    } catch (err) {
      console.error('[FormRenderer] Error during submit:', err);
      setMessage({ type: 'error', text: 'An unexpected error occurred' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="component-container form-component" style={{ padding: '20px', border: '1px solid #3b4252', margin: '15px 0', borderRadius: '8px', backgroundColor: '#242936' }}>
      <h3 style={{ marginBottom: '15px', color: '#646cff' }}>{component.name}</h3>
      
      {message && (
        <div style={{
          padding: '10px',
          marginBottom: '15px',
          borderRadius: '4px',
          backgroundColor: message.type === 'success' ? 'rgba(76, 175, 80, 0.1)' : 'rgba(244, 67, 54, 0.1)',
          color: message.type === 'success' ? '#4caf50' : '#f44336',
          border: `1px solid ${message.type === 'success' ? '#4caf50' : '#f44336'}`
        }}>
          {message.text}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        {component.fields?.map((field, index) => (
          <div key={index} style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
            <label style={{ fontSize: '0.9rem', color: '#a6accd', textTransform: 'capitalize' }}>
              {field}
            </label>
            <input 
              type="text"
              value={values[field] || ''}
              onChange={(e) => handleChange(field, e.target.value)}
              placeholder={`Enter ${field}...`}
              disabled={loading}
              style={{
                padding: '10px 12px',
                borderRadius: '4px',
                border: '1px solid #3b4252',
                backgroundColor: '#1a1d27',
                color: '#fff',
                opacity: loading ? 0.7 : 1
              }}
            />
          </div>
        ))}
        <button 
          type="submit"
          disabled={loading}
          style={{
            marginTop: '10px',
            padding: '12px',
            borderRadius: '4px',
            border: 'none',
            backgroundColor: loading ? '#444' : '#646cff',
            color: loading ? '#888' : 'white',
            fontWeight: 'bold',
            cursor: loading ? 'not-allowed' : 'pointer',
            transition: 'background-color 0.2s'
          }}
        >
          {loading ? 'Processing...' : 'Submit'}
        </button>
      </form>
    </div>
  );
}
