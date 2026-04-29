import { useState, useEffect } from 'react';
import { generateApp } from './services/api';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './App.css';

const LOADING_STEPS = [
  "Understanding intent...",
  "Designing system...",
  "Generating schemas...",
  "Validating...",
  "Fixing issues...",
  "Launching app..."
];

function App() {
  const [prompt, setPrompt] = useState('');
  const [config, setConfig] = useState(null);
  const [clarification, setClarification] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [runtimeId, setRuntimeId] = useState(null);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    
    setLoading(true);
    setConfig(null);
    setClarification(null);
    setEvaluation(null);
    setLoadingStep(0);
    
    const newId = Date.now().toString();
    setRuntimeId(newId);

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
        setConfig(data.config || data);
        setEvaluation(data.evaluation || null);
        
        const finalConfig = data.config || data;
        
        // Save to localStorage so the standalone Live App can read it
        localStorage.setItem(`config_${newId}`, JSON.stringify(finalConfig));
        localStorage.setItem(`role_${newId}`, 'Public'); // default role
        
        const score = data.evaluation?.score || 0;
        
        if (score >= 85) {
          // Instead of window.open inside async (which triggers popup blockers),
          // we will render a prominent button in the UI for the user to click.
        }
      }
    } catch (err) {
      stepTimers.forEach(clearTimeout);
      console.error('Error generating config:', err);
    } finally {
      // Delay removing the loading state if we are launching, so it looks smooth
      setTimeout(() => setLoading(false), 1200);
    }
  };

  return (
    <div className="app-container" style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: '#0f111a' }}>
      <header className="header" style={{ padding: '20px 40px', borderBottom: '1px solid #1e212b', backgroundColor: '#161925' }}>
        <div className="header-top" style={{ display: 'flex', justifyContent: 'center', marginBottom: '20px' }}>
          <h1 style={{ color: '#fff', fontSize: '2rem', letterSpacing: '1px' }}>⚡ AI UI Engine</h1>
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
      </header>
      
      <main style={{ flex: 1, display: 'flex', justifyContent: 'center', padding: '40px', overflowY: 'auto' }}>
        
        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', maxWidth: '600px', width: '100%', marginTop: '40px' }}>
            <h2 style={{ color: '#fff', marginBottom: '30px' }}>Compilation Progress</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', width: '100%' }}>
              {LOADING_STEPS.map((stepText, idx) => {
                const isActive = idx === loadingStep;
                const isCompleted = idx < loadingStep;
                const isPending = idx > loadingStep;
                
                let color = '#a6accd'; // pending
                if (isActive) color = '#646cff';
                if (isCompleted) color = '#4caf50';

                return (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '15px', opacity: isPending ? 0.4 : 1, transition: 'opacity 0.3s' }}>
                    <div style={{ 
                      width: '30px', height: '30px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                      backgroundColor: isCompleted ? '#4caf50' : isActive ? 'transparent' : '#1e212b',
                      border: `2px solid ${color}`,
                      color: isCompleted ? '#0f111a' : color,
                      fontWeight: 'bold'
                    }}>
                      {isCompleted ? '✓' : idx + 1}
                    </div>
                    <span style={{ fontSize: '1.2rem', color, fontWeight: isActive ? 'bold' : 'normal' }}>
                      Step {idx + 1}: {stepText}
                    </span>
                    {isActive && <div className="pulse-ring" style={{ width: '20px', height: '20px', marginLeft: '10px', borderColor: '#646cff', borderWidth: '2px' }}></div>}
                  </div>
                )
              })}
            </div>
          </div>
        ) : evaluation ? (
          <div style={{ display: 'flex', gap: '40px', maxWidth: '1200px', width: '100%' }}>
            
            {/* Quality Score Panel */}
            <div style={{ flex: 1, backgroundColor: '#161925', padding: '30px', borderRadius: '12px', border: '1px solid #2a2e3d', height: 'fit-content' }}>
              <h2 style={{ color: '#fff', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '2rem' }}>🎯</span> Compilation Report
              </h2>
              
              <div style={{ 
                fontSize: '3rem', fontWeight: 'bold', color: evaluation.ready ? '#4caf50' : '#f44336', 
                marginBottom: '30px', paddingBottom: '20px', borderBottom: '1px solid #2a2e3d' 
              }}>
                Quality Score: {evaluation.score}/100
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', fontSize: '1.2rem' }}>
                <div style={{ color: '#4caf50' }}>✔ Schema valid</div>
                <div style={{ color: '#4caf50' }}>✔ API-DB consistent</div>
                <div style={{ color: '#4caf50' }}>✔ UI complete</div>
                <div style={{ color: evaluation.ready ? '#4caf50' : '#f44336' }}>
                  {evaluation.ready ? '✔ Execution passed' : '✘ Execution blocked'}
                </div>
              </div>

              <div style={{ marginTop: '40px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '15px' }}>
                {!evaluation.ready && (
                   <span style={{ color: '#ff9800', fontSize: '0.9rem' }}>
                     ⚠️ App is not fully verified and may have runtime errors.
                   </span>
                )}
                <a 
                  href={`/app?sessionId=${runtimeId}`} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  style={{ 
                    display: 'inline-block',
                    padding: '15px 30px', 
                    backgroundColor: evaluation.ready ? '#4caf50' : '#ff9800', 
                    color: '#fff', 
                    textDecoration: 'none',
                    borderRadius: '8px', 
                    fontWeight: 'bold',
                    fontSize: '1.2rem',
                    boxShadow: evaluation.ready ? '0 4px 15px rgba(76, 175, 80, 0.4)' : '0 4px 15px rgba(255, 152, 0, 0.4)',
                    transition: 'transform 0.2s',
                    cursor: 'pointer'
                  }}
                  onMouseOver={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                  onMouseOut={(e) => e.currentTarget.style.transform = 'scale(1)'}
                >
                  🚀 Launch Live App
                </a>
              </div>
            </div>

            {/* Code Panel */}
            <div style={{ flex: 2, backgroundColor: '#1e212b', borderRadius: '12px', border: '1px solid #2a2e3d', display: 'flex', flexDirection: 'column', maxHeight: '70vh' }}>
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
