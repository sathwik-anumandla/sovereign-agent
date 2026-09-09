import React, { useState } from 'react';
import { ShieldCheck, Sparkles, User, Lock, AlertCircle, ArrowRight } from 'lucide-react';

export default function LoginScreen({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 2FA Challenge state
  const [requires2FA, setRequires2FA] = useState(false);
  const [tempToken, setTempToken] = useState(null);
  const [totpCode, setTotpCode] = useState('');

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!username.trim() || !password.trim() || loading) return;

    setError(null);
    setLoading(true);

    try {
      const res = await fetch('http://localhost:8000/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password: password.trim() })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Login failed. Invalid username or password.');
      }

      if (data.requires_2fa) {
        setRequires2FA(true);
        setTempToken(data.temp_token);
        setTotpCode('');
        return;
      }

      onLoginSuccess(data.access_token, data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify2FA = async (e) => {
    if (e) e.preventDefault();
    if (!totpCode.trim() || loading || !tempToken) return;

    setError(null);
    setLoading(true);

    try {
      const res = await fetch('http://localhost:8000/auth/login/verify-2fa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ temp_token: tempToken, code: totpCode.trim() })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || '2FA verification failed. Invalid code or recovery code.');
      }

      onLoginSuccess(data.access_token, data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-screen items-center justify-center app-bg p-4 theme-text-primary">
      <div className="w-full max-w-md space-y-6 rounded-3xl card-bg p-8 shadow-2xl border-0">
        {/* Header Icon & Title */}
        <div className="text-center space-y-2">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] shadow-md border-0">
            <Sparkles className="h-7 w-7" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight theme-text-primary">
            Sovereign AI Workbench
          </h2>
          <p className="text-xs theme-text-muted">
            Air-gapped enterprise workbench running locally on organization GPU server.
          </p>
        </div>

        {/* Error Alert Banner */}
        {error && (
          <div className="flex items-center gap-2 rounded-xl bg-red-500/10 p-3 text-xs text-red-400 border-0 font-sans">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Login Form or 2FA Verification Form */}
        {requires2FA ? (
          <form onSubmit={handleVerify2FA} className="space-y-4">
            <div className="space-y-1 text-center">
              <div className="flex h-10 w-10 mx-auto items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <label className="text-xs font-bold theme-text-primary block pt-1">
                Enter 2FA Code or Emergency Recovery Code
              </label>
              <p className="text-[11px] theme-text-muted">
                Open your authenticator app (Google Auth, Microsoft Auth, YubiKey) and enter the 6-digit TOTP code.
              </p>
            </div>

            <div className="relative">
              <input
                type="text"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                placeholder="000000 or xxxx-xxxx"
                className="w-full rounded-xl border-0 input-bg py-3 px-3 text-center font-mono text-base tracking-widest theme-text-primary focus:outline-none focus:ring-0"
                required
                autoFocus
              />
            </div>

            <button
              type="submit"
              disabled={loading || !totpCode.trim()}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] py-3 text-xs font-bold shadow-md hover:opacity-90 transition-all border-0 cursor-pointer disabled:opacity-50"
            >
              <span>{loading ? 'Verifying Code...' : 'Verify & Continue'}</span>
              {!loading && <ArrowRight className="h-4 w-4" />}
            </button>

            <button
              type="button"
              onClick={() => { setRequires2FA(false); setTempToken(null); setError(null); }}
              className="w-full text-center text-xs theme-text-muted hover:theme-text-primary border-0 bg-transparent cursor-pointer pt-1"
            >
              Back to Password Sign In
            </button>
          </form>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <label className="text-xs font-semibold theme-text-primary px-1">
                Username
              </label>
              <div className="relative">
                <User className="absolute left-3 top-3 h-4 w-4 theme-text-muted" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter username"
                  className="w-full rounded-xl border-0 input-bg py-2.5 pl-9 pr-3 text-sm theme-text-primary placeholder:theme-text-muted focus:outline-none focus:ring-0"
                  required
                  autoComplete="username"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold theme-text-primary px-1">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 h-4 w-4 theme-text-muted" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  className="w-full rounded-xl border-0 input-bg py-2.5 pl-9 pr-3 text-sm theme-text-primary placeholder:theme-text-muted focus:outline-none focus:ring-0"
                  required
                  autoComplete="current-password"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !username.trim() || !password.trim()}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] py-3 text-xs font-bold shadow-md hover:opacity-90 transition-all border-0 cursor-pointer disabled:opacity-50"
            >
              <span>{loading ? 'Authenticating...' : 'Sign In to Sovereign Workbench'}</span>
              {!loading && <ArrowRight className="h-4 w-4" />}
            </button>
          </form>
        )}

        {/* Quick Demo Login Preset Buttons */}
        <div className="space-y-2 pt-2 border-t border-[var(--border-muted)]">
          <div className="text-[11px] font-semibold theme-text-muted text-center">
            Demo Test Accounts:
          </div>
          <div className="flex gap-2 justify-center text-xs">
            <button
              type="button"
              onClick={() => { setUsername('engineer1'); setPassword('engineer123'); }}
              className="rounded-lg input-bg px-2.5 py-1.5 theme-text-primary hover:opacity-80 transition-all border-0 cursor-pointer"
            >
              Engineer
            </button>
            <button
              type="button"
              onClick={() => { setUsername('admin'); setPassword('admin123'); }}
              className="rounded-lg input-bg px-2.5 py-1.5 theme-text-primary hover:opacity-80 transition-all border-0 cursor-pointer"
            >
              Admin
            </button>
            <button
              type="button"
              onClick={() => { setUsername('analyst1'); setPassword('analyst123'); }}
              className="rounded-lg input-bg px-2.5 py-1.5 theme-text-primary hover:opacity-80 transition-all border-0 cursor-pointer"
            >
              Analyst
            </button>
          </div>
        </div>

        {/* Air-Gap Security Footer Note */}
        <div className="flex items-center justify-center gap-1.5 text-[11px] theme-text-muted font-mono pt-2">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
          <span>Air-Gapped HMAC JWT Auth · 0 Egress</span>
        </div>
      </div>
    </div>
  );
}
