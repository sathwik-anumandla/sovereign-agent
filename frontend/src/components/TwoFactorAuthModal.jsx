import React, { useState, useEffect } from 'react';
import { ShieldCheck, ShieldAlert, KeyRound, Copy, Check, QrCode, AlertCircle, RefreshCw, X } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

export default function TwoFactorAuthModal({ isOpen, onClose, token, currentUser }) {
  const [isEnabled, setIsEnabled] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Setup flow state
  const [step, setStep] = useState('initial'); // 'initial' | 'setup' | 'disable'
  const [qrCodeData, setQrCodeData] = useState(null); // { secret, qr_code, backup_codes }
  const [verifyCode, setVerifyCode] = useState('');
  const [disablePassword, setDisablePassword] = useState('');
  const [disableCode, setDisableCode] = useState('');
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [copiedCodes, setCopiedCodes] = useState(false);

  useEffect(() => {
    if (isOpen && token) {
      fetch2FAStatus();
    }
  }, [isOpen, token]);

  const fetch2FAStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/2fa/status`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setIsEnabled(data.totp_enabled);
        setStep('initial');
      }
    } catch (err) {
      console.error('Error fetching 2FA status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleStartSetup = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/2fa/setup`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to generate 2FA QR code');

      setQrCodeData(data);
      setStep('setup');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmEnable = async (e) => {
    if (e) e.preventDefault();
    if (!verifyCode.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/2fa/enable`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ code: verifyCode.trim() })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Invalid verification code');

      setIsEnabled(true);
      setSuccessMsg('Two-Factor Authentication (2FA) is now active on your account!');
      setStep('initial');
      setVerifyCode('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDisable2FA = async (e) => {
    if (e) e.preventDefault();
    if (!disablePassword.trim() || !disableCode.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/2fa/disable`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          password: disablePassword.trim(),
          code: disableCode.trim()
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to disable 2FA');

      setIsEnabled(false);
      setSuccessMsg('Two-Factor Authentication (2FA) has been disabled.');
      setStep('initial');
      setDisablePassword('');
      setDisableCode('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCopySecret = () => {
    if (qrCodeData?.secret) {
      navigator.clipboard.writeText(qrCodeData.secret);
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 2000);
    }
  };

  const handleCopyBackupCodes = () => {
    if (qrCodeData?.backup_codes) {
      navigator.clipboard.writeText(qrCodeData.backup_codes.join('\n'));
      setCopiedCodes(true);
      setTimeout(() => setCopiedCodes(false), 2000);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 font-sans theme-text-primary">
      <div className="w-full max-w-lg rounded-3xl card-bg p-6 shadow-2xl border border-[var(--border-muted)] space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--border-muted)] pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold theme-text-primary">Two-Factor Security (2FA)</h3>
              <p className="text-xs theme-text-muted">Air-gapped TOTP Authenticator & Backup Codes</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 theme-text-muted hover:bg-[var(--bg-hover)] transition-colors border-0 cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Alerts */}
        {error && (
          <div className="flex items-center gap-2 rounded-xl bg-red-500/10 p-3 text-xs text-red-400 font-mono">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="flex items-center gap-2 rounded-xl bg-emerald-500/10 p-3 text-xs text-emerald-400 font-mono">
            <ShieldCheck className="h-4 w-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Initial Overview Screen */}
        {step === 'initial' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-2xl bg-[var(--bg-input)] p-4 border border-[var(--border-muted)]">
              <div className="flex items-center gap-3">
                {isEnabled ? (
                  <ShieldCheck className="h-6 w-6 text-emerald-400 shrink-0" />
                ) : (
                  <ShieldAlert className="h-6 w-6 text-amber-400 shrink-0" />
                )}
                <div>
                  <div className="text-sm font-semibold theme-text-primary">
                    {isEnabled ? '2FA Protection Active' : '2FA Protection Disabled'}
                  </div>
                  <div className="text-xs theme-text-muted">
                    {isEnabled
                      ? 'Account secured with TOTP authenticator app & single-use backup codes.'
                      : 'Add an extra layer of security to prevent unauthorized access.'}
                  </div>
                </div>
              </div>
              <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase font-mono ${
                isEnabled ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
              }`}>
                {isEnabled ? 'ACTIVE' : 'INACTIVE'}
              </span>
            </div>

            {isEnabled ? (
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleStartSetup}
                  disabled={loading}
                  className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-[var(--bg-input)] hover:bg-[var(--bg-hover)] theme-text-primary py-2.5 text-xs font-semibold border border-[var(--border-muted)] cursor-pointer transition-colors"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  <span>Re-configure Authenticator</span>
                </button>
                <button
                  type="button"
                  onClick={() => setStep('disable')}
                  className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-400 py-2.5 text-xs font-semibold border border-red-500/20 cursor-pointer transition-colors"
                >
                  <span>Disable 2FA</span>
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={handleStartSetup}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-[var(--palette-slate-dark)] text-[var(--palette-warm-sand)] py-3 text-xs font-bold shadow-md hover:opacity-90 transition-all border-0 cursor-pointer"
              >
                <QrCode className="h-4 w-4" />
                <span>{loading ? 'Generating Setup QR...' : 'Set Up TOTP 2FA Authenticator'}</span>
              </button>
            )}
          </div>
        )}

        {/* Step 2: Setup QR Code & Backup Codes */}
        {step === 'setup' && qrCodeData && (
          <form onSubmit={handleConfirmEnable} className="space-y-4">
            <div className="space-y-3">
              <div className="text-xs font-semibold theme-text-primary">
                1. Scan QR Code in Authenticator App
              </div>
              <div className="flex flex-col sm:flex-row items-center gap-4 rounded-2xl bg-[var(--bg-input)] p-4 border border-[var(--border-muted)]">
                {qrCodeData.qr_code && (
                  <img
                    src={qrCodeData.qr_code}
                    alt="2FA TOTP QR Code"
                    className="h-32 w-32 rounded-xl bg-white p-1 border border-gray-300 shrink-0"
                  />
                )}
                <div className="space-y-2 text-xs">
                  <p className="theme-text-muted">
                    Scan with Google Authenticator, Microsoft Authenticator, YubiKey, or Aegis.
                  </p>
                  <div className="space-y-1 font-mono">
                    <span className="text-[10px] theme-text-muted block">Secret Key (Manual Entry):</span>
                    <div className="flex items-center gap-2">
                      <code className="bg-black/30 px-2 py-1 rounded text-[11px] text-amber-300 tracking-widest select-all">
                        {qrCodeData.secret}
                      </code>
                      <button
                        type="button"
                        onClick={handleCopySecret}
                        className="rounded p-1 theme-text-muted hover:theme-text-primary border-0 bg-transparent cursor-pointer"
                        title="Copy Secret"
                      >
                        {copiedSecret ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Emergency Recovery Codes */}
            {qrCodeData.backup_codes && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold theme-text-primary flex items-center gap-1.5">
                    <KeyRound className="h-3.5 w-3.5 text-amber-400" />
                    <span>2. Single-Use Emergency Recovery Codes</span>
                  </div>
                  <button
                    type="button"
                    onClick={handleCopyBackupCodes}
                    className="flex items-center gap-1 text-[10px] theme-text-muted hover:theme-text-primary border-0 bg-transparent cursor-pointer font-mono"
                  >
                    {copiedCodes ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                    <span>{copiedCodes ? 'Copied' : 'Copy All'}</span>
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-1.5 rounded-2xl bg-black/30 p-3 font-mono text-[11px] text-emerald-400 border border-[var(--border-muted)]">
                  {qrCodeData.backup_codes.map((code, i) => (
                    <div key={i} className="bg-white/5 px-2 py-1 rounded text-center font-bold tracking-wider">
                      {code}
                    </div>
                  ))}
                </div>
                <p className="text-[10px] theme-text-muted">
                  Save these single-use recovery codes in a secure location. You can use them to sign in if you lose your authenticator device.
                </p>
              </div>
            )}

            {/* Verification Code Confirmation Input */}
            <div className="space-y-2 pt-2 border-t border-[var(--border-muted)]">
              <label className="text-xs font-semibold theme-text-primary block">
                3. Verify 6-Digit Authenticator Code
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  maxLength={6}
                  value={verifyCode}
                  onChange={(e) => setVerifyCode(e.target.value)}
                  placeholder="000000"
                  className="flex-1 rounded-xl border-0 input-bg py-2.5 px-3 text-center font-mono text-base tracking-widest theme-text-primary focus:outline-none focus:ring-0"
                  required
                />
                <button
                  type="submit"
                  disabled={loading || verifyCode.length < 6}
                  className="rounded-xl bg-emerald-600 text-white px-5 text-xs font-bold hover:bg-emerald-500 transition-colors border-0 cursor-pointer disabled:opacity-50"
                >
                  {loading ? 'Activating...' : 'Activate 2FA'}
                </button>
              </div>
            </div>
          </form>
        )}

        {/* Disable 2FA Screen */}
        {step === 'disable' && (
          <form onSubmit={handleDisable2FA} className="space-y-4">
            <div className="text-xs theme-text-muted">
              To disable Two-Factor Authentication, enter your account password and a valid 6-digit code or recovery code.
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold theme-text-primary block">Account Password</label>
              <input
                type="password"
                value={disablePassword}
                onChange={(e) => setDisablePassword(e.target.value)}
                placeholder="Enter password"
                className="w-full rounded-xl border-0 input-bg py-2.5 px-3 text-sm theme-text-primary focus:outline-none focus:ring-0"
                required
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold theme-text-primary block">6-Digit TOTP or Recovery Code</label>
              <input
                type="text"
                value={disableCode}
                onChange={(e) => setDisableCode(e.target.value)}
                placeholder="000000 or xxxx-xxxx"
                className="w-full rounded-xl border-0 input-bg py-2.5 px-3 font-mono text-sm theme-text-primary focus:outline-none focus:ring-0"
                required
              />
            </div>

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => setStep('initial')}
                className="flex-1 rounded-xl bg-[var(--bg-input)] hover:bg-[var(--bg-hover)] theme-text-primary py-2.5 text-xs font-semibold border-0 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading || !disablePassword || !disableCode}
                className="flex-1 rounded-xl bg-red-600 text-white py-2.5 text-xs font-bold hover:bg-red-500 border-0 cursor-pointer disabled:opacity-50"
              >
                {loading ? 'Disabling...' : 'Confirm & Disable 2FA'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
