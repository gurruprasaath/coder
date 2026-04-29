import React, { useState, useEffect } from 'react';
import { handleAction } from '../services/runtimeEngine';

export default function TableRenderer({ component, config, runtimeId, onAction }) {
  const fields = component.fields || [];
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      const endpoint = component.endpoint_ref || '';
      
      // Update debug panel state
      if (onAction) onAction(endpoint);

      const response = await handleAction(endpoint, null, config, runtimeId);
      if (response.success && response.data) {
        setData(response.data);
      } else {
        setData([]);
      }
      setLoading(false);
    };

    fetchData();
  }, [component.endpoint_ref]);

  return (
    <div className="component-container table-component" style={{ padding: '20px', border: '1px solid #3b4252', margin: '15px 0', borderRadius: '8px', backgroundColor: '#242936', overflowX: 'auto' }}>
      <h3 style={{ marginBottom: '15px', color: '#646cff' }}>{component.name}</h3>
      
      {loading ? (
        <div style={{ padding: '20px', color: '#888', fontStyle: 'italic' }}>Loading data...</div>
      ) : data.length === 0 ? (
        <div style={{ padding: '20px', color: '#888', fontStyle: 'italic' }}>No data available</div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #3b4252' }}>
              {fields.map((field, index) => (
                <th key={index} style={{ padding: '12px', color: '#a6accd', textTransform: 'capitalize' }}>
                  {field}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, rowIndex) => (
              <tr key={rowIndex} style={{ borderBottom: '1px solid #2a2e3d' }}>
                {fields.map((field, colIndex) => (
                  <td key={colIndex} style={{ padding: '12px', color: '#e0e0e0' }}>
                    {row[field] !== undefined ? String(row[field]) : ''}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
