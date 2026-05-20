import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTelegramAuth } from '../hooks/useTelegramAuth';
import './Login.css';

const Login: React.FC = () => {
  const { setIsAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string })?.from ?? '/';

  const auth = useTelegramAuth({
    onSuccess: () => {
      setIsAuthenticated(true);
      navigate(from, { replace: true });
    },
  });

  return (
    <div className="login-container">
      <div className="login-card">
        <h1 className="login-title">Профайлер</h1>
        <p className="login-subtitle">Войдите через Telegram</p>

        {auth.error && <div className="error-message">{auth.error}</div>}

        {auth.step === 'phone' && (
          <form onSubmit={auth.sendCode}>
            <div className="form-group">
              <label htmlFor="phone">Номер телефона</label>
              <input
                id="phone"
                type="tel"
                placeholder="+7 (999) 999-99-99"
                value={auth.phone}
                onChange={e => auth.setPhone(e.target.value)}
                required
                disabled={auth.loading}
              />
            </div>
            <button type="submit" disabled={auth.loading} className="submit-button">
              {auth.loading ? 'Отправка...' : 'Отправить код'}
            </button>
          </form>
        )}

        {auth.step === 'code' && (
          <form onSubmit={auth.verifyCode}>
            <div className="form-group">
              <label htmlFor="code">Код подтверждения</label>
              <input
                id="code"
                type="text"
                placeholder="Введите код из Telegram"
                value={auth.code}
                onChange={e => auth.setCode(e.target.value)}
                required
                disabled={auth.loading}
              />
            </div>
            <button type="submit" disabled={auth.loading} className="submit-button">
              {auth.loading ? 'Проверка...' : 'Подтвердить'}
            </button>
            <button type="button" onClick={auth.reset} className="back-button">
              Назад
            </button>
          </form>
        )}

        {auth.step === '2fa' && (
          <form onSubmit={auth.verify2FA}>
            <div className="form-group">
              <label htmlFor="twofa">Пароль двухфакторной аутентификации</label>
              <input
                id="twofa"
                type="password"
                placeholder="Введите пароль"
                value={auth.twoFa}
                onChange={e => auth.setTwoFa(e.target.value)}
                required
                disabled={auth.loading}
              />
            </div>
            <button type="submit" disabled={auth.loading} className="submit-button">
              {auth.loading ? 'Проверка...' : 'Подтвердить'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default Login;
