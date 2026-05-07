import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Phone, LogOut, CheckCircle, Loader } from 'lucide-react';
import '../styles/TelegramAuth.css';

const TelegramAuth: React.FC = () => {
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);
  const [step, setStep] = useState<'status' | 'phone' | 'code' | '2fa'>('status');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [phoneCodeHash, setPhoneCodeHash] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const res = await api.get('/api/telegram/auth/status');
      setIsAuthorized(res.data.authorized);
      if (res.data.authorized) {
        setStep('status');
      } else {
        setStep('phone');
      }
    } catch (err: any) {
      setError('Failed to check auth status');
    }
  };

  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await api.post('/api/telegram/auth/send_code', { phone });
      setPhoneCodeHash(res.data.phone_code_hash);
      setStep('code');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send code');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await api.post('/api/telegram/auth/verify', {
        phone,
        code,
        phone_code_hash: phoneCodeHash,
      });
      if (res.data.status === 'requires_2fa') {
        setStep('2fa');
      } else {
        setIsAuthorized(true);
        setStep('status');
        setPhone('');
        setCode('');
        setPassword('');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify2FA = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.post('/api/telegram/auth/2fa', { password });
      setIsAuthorized(true);
      setStep('status');
      setPhone('');
      setCode('');
      setPassword('');
    } catch (err: any) {
      setError(err.response?.data?.detail || '2FA failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    setLoading(true);
    try {
      await api.post('/api/telegram/auth/logout');
      setIsAuthorized(false);
      setStep('phone');
    } catch (err: any) {
      setError('Logout failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="telegram-auth-card serpent-card">
      <div className="auth-header">
        <Phone size={24} className="phone-icon" />
        <h3>Telegram Authentication</h3>
      </div>

      {error && <div className="auth-error">{error}</div>}

      {isAuthorized === null ? (
        <div className="auth-loading">
          <Loader className="spinner" size={24} />
          <span>Checking status...</span>
        </div>
      ) : isAuthorized ? (
        <div className="auth-success">
          <CheckCircle size={32} className="success-icon" />
          <p className="success-text">✅ Telegram Connected</p>
          <button
            className="btn-logout"
            onClick={handleLogout}
            disabled={loading}
          >
            <LogOut size={16} />
            Disconnect
          </button>
        </div>
      ) : (
        <div className="auth-forms">
          {step === 'phone' && (
            <form onSubmit={handleSendCode}>
              <label>Phone Number</label>
              <input
                type="tel"
                placeholder="+38... or 38..."
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                disabled={loading}
                required
              />
              <button type="submit" disabled={loading} className="btn-primary">
                {loading ? 'Sending...' : 'Send Code'}
              </button>
            </form>
          )}

          {step === 'code' && (
            <form onSubmit={handleVerifyCode}>
              <label>Verification Code</label>
              <input
                type="text"
                placeholder="Enter the code from Telegram"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                disabled={loading}
                required
              />
              <button type="submit" disabled={loading} className="btn-primary">
                {loading ? 'Verifying...' : 'Verify'}
              </button>
            </form>
          )}

          {step === '2fa' && (
            <form onSubmit={handleVerify2FA}>
              <label>Two-Factor Password</label>
              <input
                type="password"
                placeholder="Enter your 2FA password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
                required
              />
              <button type="submit" disabled={loading} className="btn-primary">
                {loading ? 'Verifying...' : 'Verify 2FA'}
              </button>
            </form>
          )}
        </div>
      )}
    </div>
  );
};

export default TelegramAuth;
