import React, { useCallback, useEffect, useState } from 'react';
import './App.css';
import ApprovalsPanel from './ApprovalsPanel';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: Array<{ source: string; snippet: string }>;
  confidence?: number | null;
  workflow?: string | null;
  traceId?: string;
}

interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: string;
}

const API_BASE = 'http://localhost:8000';
const TOKEN_KEY = 'procurement_token';

function Login({ onLogin }: { onLogin: (token: string) => void }) {
  const [email, setEmail] = useState('manager@example.com');
  const [password, setPassword] = useState('demo123');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json();
      if (!response.ok) {
        setError(data.detail || 'Login failed');
        return;
      }
      onLogin(data.access_token);
    } catch {
      setError('Could not reach the API');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-wrapper">
      <form className="login-card" onSubmit={submit}>
        <h1>Procurement AI Platform</h1>
        <p>Sign in to access procurement operations</p>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        {error && <div className="login-error">{error}</div>}
        <button type="submit" disabled={loading}>
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
        <div className="login-hint">
          Demo: manager@example.com / demo123
        </div>
      </form>
    </div>
  );
}

function App() {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(TOKEN_KEY)
  );
  const [user, setUser] = useState<AuthUser | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    setMessages([]);
  }, []);

  useEffect(() => {
    if (!token) {
      setUser(null);
      return;
    }
    fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (!response.ok) {
          logout();
          return null;
        }
        return response.json();
      })
      .then((data) => data && setUser(data))
      .catch(() => logout());
  }, [token, logout]);

  const handleLogin = (newToken: string) => {
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading || !token) return;

    const question = input;
    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: question,
          session_id: 'ui-session',
        }),
      });

      if (response.status === 401) {
        logout();
        return;
      }

      const data = await response.json();
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response,
          citations: data.citations,
          confidence: data.confidence,
          workflow: data.workflow,
          traceId: data.trace_id,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="App">
      <header className="App-header">
        <div>
          <h1>Procurement AI Platform</h1>
          <p>Ask about invoices, purchase orders, contracts, payments, and policies</p>
        </div>
        {user && (
          <div className="user-bar">
            <span>
              {user.name} · <strong>{user.role}</strong>
            </span>
            <button onClick={logout}>Sign out</button>
          </div>
        )}
      </header>

      <main className="App-main">
        <div className="chat-container">
          <div className="messages">
            {messages.length === 0 && (
              <div className="empty-state">
                <p>Try:</p>
                <ul>
                  <li>Why is invoice INV-000010 overdue?</li>
                  <li>Does INV-000010 comply with its purchase order?</li>
                  <li>Find potential duplicate invoices</li>
                  <li>What are the approval requirements for invoices over 50000?</li>
                  <li>Request payment for INV-000003</li>
                </ul>
              </div>
            )}

            {messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.role}`}>
                <div className="message-content">{msg.content}</div>
                {msg.workflow && (
                  <div className="message-meta">
                    workflow: {msg.workflow}
                    {msg.confidence != null &&
                      ` · confidence: ${Math.round(msg.confidence * 100)}%`}
                  </div>
                )}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="citations">
                    <strong>Sources:</strong>
                    <ul>
                      {msg.citations.map((cite, i) => (
                        <li key={i}>
                          <code>{cite.source}</code>
                          {cite.snippet && `: ${cite.snippet.slice(0, 160)}`}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
            {loading && <div className="message assistant loading">Investigating…</div>}
          </div>

          <form onSubmit={handleSubmit} className="input-form">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about invoices, POs, contracts..."
              disabled={loading}
            />
            <button type="submit" disabled={loading || !input.trim()}>
              Send
            </button>
          </form>
        </div>

        <ApprovalsPanel token={token} onUnauthorized={logout} />
      </main>
    </div>
  );
}

export default App;
