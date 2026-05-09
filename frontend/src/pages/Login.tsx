import React, { useState } from 'react';
import api from '../services/api';
import './Login.css';

const Login: React.FC = () => {
  const [step, setStep] = useState<'phone' | 'code' | '2fa'>('phone');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [twoFa, setTwoFa] = useState('');
  const [phoneCodeHash, setPhoneCodeHash] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await api.post('/api/telegram/auth/send_code', {
        phone: phone,
      });
      if (response.data.status === 'success') {
        setPhoneCodeHash(response.data.phone_code_hash);
        setStep('code');
      } else {
        setError(response.data.error || 'Failed to send code');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.response?.data?.error || 'Failed to send code');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await api.post('/api/telegram/auth/verify', {
        phone: phone,
        code: code,
        phone_code_hash: phoneCodeHash,
      });
      if (response.data.status === 'success') {
        if (response.data.requires_2fa) {
          setStep('2fa');
        } else {
          window.location.reload();
        }
      } else {
        setError(response.data.error || 'Failed to verify code');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.response?.data?.error || 'Failed to verify code');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify2FA = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await api.post('/api/telegram/auth/2fa', {
        password: twoFa,
      });
      if (response.data.status === 'success') {
        window.location.reload();
      } else {
        setError(response.data.error || 'Failed to verify 2FA');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.response?.data?.error || 'Failed to verify 2FA');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1 className="login-title">Профайлер</h1>
        <p className="login-subtitle">Пожалуйста, войдите через Telegram</p>

        {error && <div className="error-message">{error}</div>}

        {step === 'phone' && (
          <form onSubmit={handleSendCode}>
            <div className="form-group">
              <label htmlFor="phone">Номер телефона</label>
              <input
                id="phone"
                type="tel"
                placeholder="+7 (999) 999-99-99"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            <button type="submit" disabled={loading} className="submit-button">
              {loading ? 'Отправка...' : 'Отправить код'}
            </button>
          </form>
        )}

        {step === 'code' && (
          <form onSubmit={handleVerifyCode}>
            <div className="form-group">
              <label htmlFor="code">Код подтверждения</label>
              <input
                id="code"
                type="text"
                placeholder="Введите код из Telegram"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            <button type="submit" disabled={loading} className="submit-button">
              {loading ? 'Проверка...' : 'Подтвердить'}
            </button>
            <button
              type="button"
              onClick={() => {
                setStep('phone');
                setPhone('');
                setCode('');
                setPhoneCodeHash('');
              }}
              className="back-button"
            >
              Назад
            </button>
          </form>
        )}

        {step === '2fa' && (
          <form onSubmit={handleVerify2FA}>
            <div className="form-group">
              <label htmlFor="2fa">Пароль двухфакторной аутентификации</label>
              <input
                id="2fa"
                type="password"
                placeholder="Введите пароль"
                value={twoFa}
                onChange={(e) => setTwoFa(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            <button type="submit" disabled={loading} className="submit-button">
              {loading ? 'Проверка...' : 'Подтвердить'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default Login;
