import { useState, type FormEvent } from 'react';
import api from '../services/api';

interface TelegramAuthOptions {
  onSuccess: () => void;
  onError?: (msg: string) => void;
}

export const useTelegramAuth = ({ onSuccess, onError }: TelegramAuthOptions) => {
  const [step, setStep] = useState<'phone' | 'code' | '2fa'>('phone');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [twoFa, setTwoFa] = useState('');
  const [phoneCodeHash, setPhoneCodeHash] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const reset = () => {
    setStep('phone');
    setPhone('');
    setCode('');
    setTwoFa('');
    setPhoneCodeHash('');
    setError('');
  };

  const sendCode = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await api.post('/api/telegram/auth/send_code', { phone });
      if (res.data.status === 'success') {
        setPhoneCodeHash(res.data.phone_code_hash);
        setStep('code');
      } else {
        const msg = res.data.error || 'Не удалось отправить код';
        setError(msg);
        onError?.(msg);
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.response?.data?.error || 'Не удалось отправить код';
      setError(msg);
      onError?.(msg);
    } finally {
      setLoading(false);
    }
  };

  const verifyCode = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await api.post('/api/telegram/auth/verify', {
        phone, code, phone_code_hash: phoneCodeHash,
      });
      if (res.data.status === 'success') {
        onSuccess();
        reset();
      } else if (res.data.status === 'requires_2fa') {
        setStep('2fa');
      } else {
        const msg = res.data.message || res.data.error || 'Неверный код';
        setError(msg);
        onError?.(msg);
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.response?.data?.message || err.response?.data?.error || 'Не удалось подтвердить код';
      setError(msg);
      onError?.(msg);
    } finally {
      setLoading(false);
    }
  };

  const verify2FA = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await api.post('/api/telegram/auth/2fa', {
        phone, phone_code_hash: phoneCodeHash, password: twoFa,
      });
      if (res.data.status === 'success') {
        onSuccess();
        reset();
      } else {
        const msg = res.data.error || 'Неверный пароль 2FA';
        setError(msg);
        onError?.(msg);
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.response?.data?.error || 'Не удалось подтвердить 2FA';
      setError(msg);
      onError?.(msg);
    } finally {
      setLoading(false);
    }
  };

  return {
    step, setStep,
    phone, setPhone,
    code, setCode,
    twoFa, setTwoFa,
    loading, error,
    sendCode, verifyCode, verify2FA, reset,
  };
};
