import { useState, useEffect } from 'react';
import { generateApp, fetchEvalMetrics } from './services/api';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './App.css';

const PIPELINE_STEPS = [
  { label: 'Understanding intent',  icon: '🧠', detail: 'Parsing natural language prompt...' },
  { label: 'Designing system',      icon: '📐', detail: 'Generating entities, flows, roles...' },
  { label: 'Generating schema',     icon: '⚙️', detail: 'Building DB → API → UI layers...' },
  { label: 'Validating',            icon: '🔍', detail: 'Running cross-layer structural checks...' },
  { label: 'Repairing issues',      icon: '🔧', detail: 'Chain-of-thought targeted repair...' },
  { label: 'Launching app',         icon: '🚀', detail: 'Deploying runtime & creating tables...' },
];

function App() {
  const [prompt, setPrompt] = useState('');
  const [config, setConfig] = useState(null);
  const [clarification, setClarification] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [runtimeId, setRuntimeId] = useState(null);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [isNewGeneration, setIsNewGeneration] = useState(true);
  const [evalMetrics, setEvalMetrics] = useState(null);
  const [showMetrics, setShowMetrics] = useState(false);

  // Load metrics on mount
  useEffect(() => {
    fetchEvalMetrics().then(data => { if (data) setEvalMetrics(data); });
  }, []);

  const handleNewApp = () => {
    if (currentSessionId) {
      localStorage.removeItem(`config_${currentSessionId}`);
      localStorage.removeItem(`role_${currentSessionId}`);
    }
    setConfig(null);
    setClarification(null);
    setEvaluation(null);
    setPrompt('');
    
    const newId = Date.now().toString();
    setCurrentSessionId(newId);
    setRuntimeId(newId);
    setIsNewGeneration(true);
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    
    setLoading(true);
    setConfig(null);
    setClarification(null);
    setEvaluation(null);
    setLoadingStep(0);
    
    let usedId;
    if (isNewGeneration || !currentSessionId) {
      usedId = Date.now().toString();
      setCurrentSessionId(usedId);
      // Optional: clean up old state if desired, but localStorage handles overwrite
    } else {
      usedId = currentSessionId;
    }
    setRuntimeId(usedId);

    // UX: Fake compilation progress steps based on average pipeline durations
    const stepTimers = [
      setTimeout(() => setLoadingStep(1), 2000),  // Designing
      setTimeout(() => setLoadingStep(2), 4000),  // Generating
      setTimeout(() => setLoadingStep(3), 15000), // Validating
      setTimeout(() => setLoadingStep(4), 18000), // Fixing
    ];
    
    try {
      const data = await generateApp(prompt);

      // Clear timers since request finished
      stepTimers.forEach(clearTimeout);

      if (data.needs_clarification) {
        setClarification({
          message: data.message,
          questions: data.clarification_questions || [],
          assumptions: data.assumptions || [],
        });
      } else {
        setLoadingStep(5); // Launching app...
        const finalConfig = data.config || data;
        const evalResult = data.evaluation || null;
        setConfig(finalConfig);
        setEvaluation(evalResult);
        
        // Save to localStorage so the standalone Live App can read it
        localStorage.setItem(`config_${usedId}`, JSON.stringify(finalConfig));
        if (!localStorage.getItem(`role_${usedId}`)) {
          localStorage.setItem(`role_${usedId}`, 'Public'); // default role only if not exists
        }
        
        // Always auto-launch the live app so all buttons/forms are visible
        window.open(`/app?sessionId=${usedId}`, '_blank');
      }
    } catch (err) {
      stepTimers.forEach(clearTimeout);
      console.error('Error generating config:', err);
    } finally {
      // Delay removing the loading state if we are launching, so it looks smooth
      setTimeout(() => setLoading(false), 1200);
      // Refresh metrics after each generation
      fetchEvalMetrics().then(data => { if (data) setEvalMetrics(data); });
    }
  };

  return (
    <div className="app-container" style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: '#0f111a' }}>
      <header className="header" style={{ padding: '20px 40px', borderBottom: '1px solid #1e212b', backgroundColor: '#161925' }}>
        <div className="header-top" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div style={{ width: '180px', display: 'flex', gap: '8px' }}>
            <button 
              onClick={() => setShowMetrics(!showMetrics)}
              style={{ padding: '8px 12px', borderRadius: '6px', backgroundColor: showMetrics ? '#646cff' : 'transparent', border: '1px solid #646cff', color: showMetrics ? '#fff' : '#646cff', cursor: 'pointer', fontWeight: 'bold', fontSize: '0.8rem', transition: 'all 0.2s' }}
            >
              📊 Metrics
            </button>
          </div>
          <h1 style={{ color: '#fff', fontSize: '2rem', letterSpacing: '1px', margin: 0 }}>⚡ AI UI Engine</h1>
          <div style={{ width: '180px', textAlign: 'right' }}>
            <button 
              onClick={handleNewApp}
              disabled={loading}
              style={{ padding: '8px 16px', borderRadius: '6px', backgroundColor: 'transparent', border: '1px solid #4caf50', color: '#4caf50', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: 'bold', transition: 'all 0.2s', opacity: loading ? 0.5 : 1 }}
              onMouseOver={(e) => { if(!loading) { e.target.style.backgroundColor = '#4caf50'; e.target.style.color = '#fff'; } }}
              onMouseOut={(e) => { if(!loading) { e.target.style.backgroundColor = 'transparent'; e.target.style.color = '#4caf50'; } }}
            >
              + New App
            </button>
          </div>
        </div>
        <div className="input-group" style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', gap: '15px' }}>
          <input 
            type="text" 
            value={prompt} 
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Describe the application you want to build (e.g. A CRM with login, contacts, and dashboard)..."
            className="prompt-input"
            disabled={loading}
            style={{ flex: 1, padding: '15px 20px', borderRadius: '8px', border: '1px solid #2a2e3d', backgroundColor: '#1e212b', color: '#fff', fontSize: '1rem', outline: 'none' }}
          />
          <button 
            onClick={handleGenerate} 
            disabled={loading || !prompt.trim()}
            className="generate-btn"
            style={{ padding: '0 30px', borderRadius: '8px', backgroundColor: '#646cff', color: '#fff', border: 'none', fontWeight: 'bold', fontSize: '1rem', cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1 }}
          >
            {loading ? 'Compiling...' : 'Generate App'}
          </button>
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: '15px', gap: '30px', color: '#aaa', fontSize: '0.9rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input 
              type="radio" 
              name="generationMode" 
              checked={isNewGeneration} 
              onChange={() => setIsNewGeneration(true)} 
              disabled={loading}
              style={{ accentColor: '#646cff' }}
            />
            Create New App (Reset DB)
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: !currentSessionId || loading ? 'not-allowed' : 'pointer', opacity: !currentSessionId ? 0.5 : 1 }}>
            <input 
              type="radio" 
              name="generationMode" 
              checked={!isNewGeneration} 
              onChange={() => setIsNewGeneration(false)} 
              disabled={!currentSessionId || loading}
              style={{ accentColor: '#646cff' }}
            />
            Update Current App (Keep DB)
          </label>
        </div>
      </header>

      {/* Evaluation Metrics Dashboard */}
      {showMetrics && evalMetrics?.summary && (
        <div style={{ padding: '16px 40px', backgroundColor: '#12151e', borderBottom: '1px solid #1e212b' }}>
          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', maxWidth: '900px', margin: '0 auto' }}>
            {/* Summary Cards */}
            {[
              { label: 'Generations', value: evalMetrics.summary.total_generations, color: '#646cff' },
              { label: 'Success Rate', value: `${evalMetrics.summary.success_rate}%`, color: evalMetrics.summary.success_rate >= 80 ? '#4caf50' : evalMetrics.summary.success_rate >= 50 ? '#ff9800' : '#f44336' },
              { label: 'Avg Latency', value: `${(evalMetrics.summary.avg_latency_ms / 1000).toFixed(1)}s`, color: '#a164ff' },
              { label: 'Successes', value: evalMetrics.summary.successes, color: '#4caf50' },
              { label: 'Failures', value: evalMetrics.summary.failures, color: evalMetrics.summary.failures > 0 ? '#f44336' : '#4caf50' },
            ].map((card, i) => (
              <div key={i} style={{ flex: '1 1 120px', padding: '14px', backgroundColor: '#0d1017', borderRadius: '10px', border: '1px solid #1e212b', textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: card.color }}>{card.value}</div>
                <div style={{ fontSize: '0.72rem', color: '#555', marginTop: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{card.label}</div>
              </div>
            ))}
          </div>

          {/* Failure Types */}
          {Object.keys(evalMetrics.summary.failure_types || {}).length > 0 && (
            <div style={{ maxWidth: '900px', margin: '12px auto 0', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.75rem', color: '#555', alignSelf: 'center' }}>Top errors:</span>
              {Object.entries(evalMetrics.summary.failure_types).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([type, count], i) => (
                <span key={i} style={{ fontSize: '0.72rem', padding: '3px 8px', borderRadius: '4px', backgroundColor: 'rgba(244,67,54,0.1)', color: '#f44336', border: '1px solid rgba(244,67,54,0.2)' }}>
                  {type}: {count}
                </span>
              ))}
            </div>
          )}

          {/* Recent Logs Table */}
          {evalMetrics.logs?.length > 0 && (
            <div style={{ maxWidth: '900px', margin: '14px auto 0', maxHeight: '160px', overflowY: 'auto', borderRadius: '8px', border: '1px solid #1e212b' }}>
              <table style={{ width: '100%', fontSize: '0.75rem', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ backgroundColor: '#161925', color: '#666', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    <th style={{ padding: '8px 12px', textAlign: 'left' }}>Time</th>
                    <th style={{ padding: '8px 12px', textAlign: 'left' }}>Prompt</th>
                    <th style={{ padding: '8px 12px', textAlign: 'center' }}>Score</th>
                    <th style={{ padding: '8px 12px', textAlign: 'center' }}>API Calls</th>
                    <th style={{ padding: '8px 12px', textAlign: 'center' }}>Retries</th>
                    <th style={{ padding: '8px 12px', textAlign: 'center' }}>Latency</th>
                    <th style={{ padding: '8px 12px', textAlign: 'center' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {[...evalMetrics.logs].reverse().map((log, i) => (
                    <tr key={i} style={{ borderTop: '1px solid #1e212b', backgroundColor: i % 2 === 0 ? '#0d1017' : '#0f111a' }}>
                      <td style={{ padding: '7px 12px', color: '#555', whiteSpace: 'nowrap' }}>{new Date(log.timestamp).toLocaleTimeString()}</td>
                      <td style={{ padding: '7px 12px', color: '#a6accd', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{log.prompt}</td>
                      <td style={{ padding: '7px 12px', textAlign: 'center', color: log.score >= 90 ? '#4caf50' : '#ff9800', fontWeight: 'bold' }}>{log.score}</td>
                      <td style={{ padding: '7px 12px', textAlign: 'center', color: '#a6accd' }}>{log.api_calls ?? '—'}</td>
                      <td style={{ padding: '7px 12px', textAlign: 'center', color: '#a6accd' }}>{log.retries}</td>
                      <td style={{ padding: '7px 12px', textAlign: 'center', color: '#a6accd' }}>{(log.latency_ms / 1000).toFixed(1)}s</td>
                      <td style={{ padding: '7px 12px', textAlign: 'center' }}>
                        {log.cached ? (
                          <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 'bold', backgroundColor: 'rgba(100,108,255,0.15)', color: '#646cff' }}>CACHED</span>
                        ) : (
                          <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 'bold', backgroundColor: log.success ? 'rgba(76,175,80,0.15)' : 'rgba(244,67,54,0.15)', color: log.success ? '#4caf50' : '#f44336' }}>
                            {log.success ? 'PASS' : 'FAIL'}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <main style={{ flex: 1, display: 'flex', justifyContent: 'center', padding: '40px', overflowY: 'auto' }}>
        
        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', maxWidth: '700px', width: '100%', marginTop: '20px' }}>
            {/* Terminal Header */}
            <div style={{ width: '100%', backgroundColor: '#161925', borderRadius: '12px 12px 0 0', border: '1px solid #2a2e3d', borderBottom: 'none', padding: '12px 20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#ff5f56' }}></div>
              <div style={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#ffbd2e' }}></div>
              <div style={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#27c93f' }}></div>
              <span style={{ marginLeft: '12px', color: '#666', fontSize: '0.85rem', fontFamily: 'monospace' }}>ai-compiler — pipeline</span>
            </div>

            {/* Terminal Body */}
            <div style={{ width: '100%', backgroundColor: '#0d1017', border: '1px solid #2a2e3d', borderRadius: '0 0 12px 12px', padding: '24px 28px', fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace", fontSize: '0.9rem' }}>
              {PIPELINE_STEPS.map((step, idx) => {
                const isActive = idx === loadingStep;
                const isCompleted = idx < loadingStep;
                const isPending = idx > loadingStep;

                return (
                  <div key={idx} style={{ marginBottom: idx < PIPELINE_STEPS.length - 1 ? '16px' : 0, opacity: isPending ? 0.25 : 1, transition: 'opacity 0.4s ease' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      {/* Status icon */}
                      {isCompleted ? (
                        <span style={{ color: '#4caf50', fontSize: '1.1rem', width: '24px', textAlign: 'center' }}>✓</span>
                      ) : isActive ? (
                        <span style={{ fontSize: '1.1rem', width: '24px', textAlign: 'center', animation: 'pulse 1.5s infinite' }}>{step.icon}</span>
                      ) : (
                        <span style={{ color: '#333', fontSize: '1.1rem', width: '24px', textAlign: 'center' }}>○</span>
                      )}

                      {/* Step label */}
                      <span style={{
                        color: isCompleted ? '#4caf50' : isActive ? '#646cff' : '#444',
                        fontWeight: isActive ? 700 : 500,
                        letterSpacing: '0.3px'
                      }}>
                        {step.label}
                      </span>

                      {/* Connector dots for active */}
                      {isActive && (
                        <span className="typing-dots" style={{ color: '#646cff', letterSpacing: '2px' }}>
                          ...
                        </span>
                      )}
                    </div>

                    {/* Detail line */}
                    {(isActive || isCompleted) && (
                      <div style={{ marginLeft: '36px', marginTop: '4px', fontSize: '0.78rem', color: isCompleted ? '#3a7a3a' : '#555', fontStyle: 'italic' }}>
                        {step.detail}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Progress bar */}
              <div style={{ marginTop: '24px', height: '3px', backgroundColor: '#1e212b', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{
                  height: '100%',
                  width: `${((loadingStep + 1) / PIPELINE_STEPS.length) * 100}%`,
                  backgroundColor: '#646cff',
                  borderRadius: '2px',
                  transition: 'width 0.6s ease'
                }}></div>
              </div>
              <div style={{ marginTop: '8px', textAlign: 'right', color: '#444', fontSize: '0.75rem' }}>
                Stage {loadingStep + 1} / {PIPELINE_STEPS.length}
              </div>
            </div>
          </div>
        ) : evaluation ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px', maxWidth: '800px', width: '100%' }}>
            
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '15px' }}>
              <span style={{ color: '#4caf50', fontSize: '1.2rem', fontWeight: 'bold' }}>
                ✅ App generated successfully and launched in a new tab!
              </span>
              <a 
                href={`/app?sessionId=${runtimeId}`} 
                target="_blank" 
                rel="noopener noreferrer"
                style={{ 
                  display: 'inline-block',
                  padding: '12px 24px', 
                  backgroundColor: '#4caf50', 
                  color: '#fff', 
                  textDecoration: 'none',
                  borderRadius: '8px', 
                  fontWeight: 'bold',
                  fontSize: '1.1rem',
                  boxShadow: '0 4px 15px rgba(76, 175, 80, 0.4)',
                  transition: 'transform 0.2s',
                  cursor: 'pointer'
                }}
                onMouseOver={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                onMouseOut={(e) => e.currentTarget.style.transform = 'scale(1)'}
              >
                🚀 Open App Again
              </a>
            </div>

            {/* Code Panel */}
            <div style={{ width: '100%', backgroundColor: '#1e212b', borderRadius: '12px', border: '1px solid #2a2e3d', display: 'flex', flexDirection: 'column', maxHeight: '60vh' }}>
               <div style={{ padding: '15px 20px', borderBottom: '1px solid #2a2e3d', backgroundColor: '#161925', borderRadius: '12px 12px 0 0' }}>
                 <h3 style={{ margin: 0, color: '#a6accd' }}>Generated System JSON</h3>
               </div>
               <div style={{ flex: 1, overflowY: 'auto' }}>
                 <SyntaxHighlighter 
                    language="json" 
                    style={atomDark} 
                    customStyle={{ margin: 0, background: 'transparent' }}
                  >
                    {JSON.stringify(config, null, 2)}
                  </SyntaxHighlighter>
               </div>
            </div>

          </div>
        ) : clarification ? (
           <div className="clarification-card" style={{ maxWidth: '800px', width: '100%', margin: '0 auto' }}>
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

            <p className="clarification-hint">
              💡 Refine your prompt above with more detail and regenerate.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#a6accd', opacity: 0.5 }}>
            <div style={{ fontSize: '4rem', marginBottom: '20px' }}>🏗️</div>
            <p style={{ fontSize: '1.2rem' }}>Awaiting your instructions...</p>
          </div>
        )}
        
      </main>
    </div>
  );
}

export default App;
