import { useState, useEffect } from 'react';
import { generateApp } from './services/api';
import Renderer from './components/Renderer';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './App.css';

function App() {
  const [prompt, setPrompt] = useState('');
  const [config, setConfig] = useState(null);
  const [clarification, setClarification] = useState(null);
  const [evaluation, setEvaluation] = useState(null); // { ready, score, status, errors, warnings, metrics }
  const [loading, setLoading] = useState(false);
  const [currentRole, setCurrentRole] = useState('Public');
  const [runtimeId, setRuntimeId] = useState(null);
  const [viewMode, setViewMode] = useState('split');

  // Read role from local storage whenever runtime changes
  useEffect(() => {
    if (runtimeId) {
      const savedRole = localStorage.getItem(`role_${runtimeId}`);
      setCurrentRole(savedRole || 'Public');
    }
  }, [runtimeId]);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    
    setLoading(true);
    setConfig(null);
    setClarification(null);
    
    // Generate new runtime identity for complete state isolation
    const newId = Date.now().toString();
    setRuntimeId(newId);
    
    try {
      const data = await generateApp(prompt);

      if (data.needs_clarification) {
        setClarification({
          message: data.message,
          questions: data.clarification_questions || [],
          assumptions: data.assumptions || [],
        });
      } else {
        setConfig(data.config || data);
        setEvaluation(data.evaluation || null);
      }
    } catch (err) {
      console.error('Error generating config:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <div className="header-top">
          <h1>⚡ AI UI Engine</h1>
          <div className="view-toggles">
            <button className={`toggle-btn ${viewMode === 'code' ? 'active' : ''}`} onClick={() => setViewMode('code')}>Schema</button>
            <button className={`toggle-btn ${viewMode === 'split' ? 'active' : ''}`} onClick={() => setViewMode('split')}>Split</button>
            <button className={`toggle-btn ${viewMode === 'app' ? 'active' : ''}`} onClick={() => setViewMode('app')}>Live App</button>
          </div>
        </div>
        <div className="input-group">
          <input 
            type="text" 
            value={prompt} 
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe the application you want to build..."
            className="prompt-input"
            disabled={loading}
          />
          <button 
            onClick={handleGenerate} 
            disabled={loading || !prompt.trim()}
            className="generate-btn"
          >
            {loading ? 'Compiling...' : 'Generate App'}
          </button>
        </div>
      </header>
      
      <main className={`split-view mode-${viewMode}`}>
        {(viewMode === 'split' || viewMode === 'code') && (
          <section className="panel json-panel">
            <div className="panel-header">
              <h2>JSON Schema Output</h2>
            </div>
            <div className="panel-content json-content">
              {clarification ? (
                <div className="clarification-card">
                  <div className="clarification-icon">🤔</div>
                  <h3>Clarification Needed</h3>
                  <p className="clarification-message">{clarification.message}</p>

                  <div className="clarification-section">
                    <h4>Please answer these questions:</h4>
                    <ul>
                      {clarification.questions.map((q, i) => (
                        <li key={i}>{q}</li>
                      ))}
                    </ul>
                  </div>

                  {clarification.assumptions?.length > 0 && (
                    <div className="clarification-section assumptions">
                      <h4>Assumptions made so far:</h4>
                      <ul>
                        {clarification.assumptions.map((a, i) => (
                          <li key={i}>{a}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <p className="clarification-hint">
                    💡 Refine your prompt above with more detail and regenerate.
                  </p>
                </div>
              ) : config ? (
                <SyntaxHighlighter 
                  language="json" 
                  style={atomDark} 
                  customStyle={{ margin: 0, borderRadius: '0 0 8px 8px', background: 'transparent' }}
                  wrapLines={true}
                >
                  {JSON.stringify(config, null, 2)}
                </SyntaxHighlighter>
              ) : (
                <div className="placeholder">
                  <div className="pulse-ring"></div>
                  <p>Awaiting Configuration...</p>
                </div>
              )}
            </div>
          </section>
        )}
        
        {(viewMode === 'split' || viewMode === 'app') && (
          <section className="panel preview-panel">
            <div className="panel-header">
              <h2>Live App Preview</h2>
              {evaluation && (
                <div className={`eval-badge eval-badge--${evaluation.status?.toLowerCase()}`}>
                  <span className="eval-score">{evaluation.score}</span>
                  <span className="eval-label">
                    {evaluation.status === 'READY' && '✓ Ready'}
                    {evaluation.status === 'READY_WITH_WARNINGS' && '⚠ Warnings'}
                    {evaluation.status === 'NOT_READY' && '✗ Not Ready'}
                  </span>
                  {evaluation.metrics && (
                    <span className="eval-meta">
                      {evaluation.metrics.table_count}T · {evaluation.metrics.endpoint_count}E · {evaluation.metrics.page_count}P
                    </span>
                  )}
                </div>
              )}
            </div>
            <div className="panel-content preview-content">
              <Renderer config={config} currentRole={currentRole} setCurrentRole={setCurrentRole} runtimeId={runtimeId} />
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
