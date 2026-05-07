import React, { useState, useCallback } from 'react';
import useSWR, { mutate } from 'swr';
import api from '../services/api';
import { Settings2, Cpu, Database, Mic, Monitor, RotateCcw, Save, CheckCircle, AlertCircle, RefreshCw, Phone, User, FolderPlus, Folder } from 'lucide-react';
import './Settings.css';

interface EffectiveSetting {
  key: string;
  value: string | number | boolean | null;
  env_value: string | number | boolean | null;
  value_type: 'string' | 'int' | 'float' | 'bool';
  description: string;
  category: string;
  source: 'db' | 'env';
  updated_at: string | null;
}

interface SettingsResponse {
  settings: EffectiveSetting[];
}

const EFFECTIVE_URL = '/api/settings/effective';
const fetcher = (url: string) => api.get(url).then(r => r.data);

const CATEGORY_META: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  llm:        { label: 'AI / LLM',    icon: <Cpu size={18} />,      color: 'purple' },
  embeddings: { label: 'Embeddings',  icon: <Database size={18} />, color: 'blue'   },
  whisper:    { label: 'Whisper STT', icon: <Mic size={18} />,      color: 'green'  },
  system:     { label: 'System',      icon: <Monitor size={18} />,  color: 'yellow' },
};

const CATEGORY_ORDER = ['llm', 'embeddings', 'whisper', 'system'];

type SaveState = 'idle' | 'saving' | 'ok' | 'err';

function SettingRow({ setting }: { setting: EffectiveSetting }) {
  const [localValue, setLocalValue] = useState<string>(String(setting.value ?? ''));
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const isDirty = localValue !== String(setting.value ?? '');

  const handleSave = async () => {
    setSaveState('saving');
    try {
      await api.put(`/api/settings/${setting.key}`, {
        value: localValue,
        value_type: setting.value_type,
      });
      await mutate(EFFECTIVE_URL);
      setSaveState('ok');
      setTimeout(() => setSaveState('idle'), 2000);
    } catch {
      setSaveState('err');
      setTimeout(() => setSaveState('idle'), 3000);
    }
  };

  const handleReset = async () => {
    setSaveState('saving');
    try {
      await api.delete(`/api/settings/${setting.key}`);
      await mutate(EFFECTIVE_URL);
      setSaveState('ok');
      setTimeout(() => setSaveState('idle'), 2000);
    } catch {
      setSaveState('idle');
    }
  };

  // Keep local value in sync when SWR revalidates and we have no pending edits
  React.useEffect(() => {
    if (!isDirty) setLocalValue(String(setting.value ?? ''));
  }, [setting.value]); // eslint-disable-line react-hooks/exhaustive-deps

  const renderInput = () => {
    if (setting.value_type === 'bool') {
      return (
        <label className="toggle-switch">
          <input
            type="checkbox"
            checked={localValue === 'true' || localValue === 'True'}
            onChange={e => setLocalValue(e.target.checked ? 'true' : 'false')}
          />
          <span className="toggle-track" />
        </label>
      );
    }
    return (
      <input
        className="setting-input"
        type={setting.value_type === 'int' || setting.value_type === 'float' ? 'number' : 'text'}
        step={setting.value_type === 'float' ? '0.01' : undefined}
        value={localValue}
        onChange={e => setLocalValue(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && isDirty && handleSave()}
      />
    );
  };

  return (
    <div className={`setting-row ${isDirty ? 'dirty' : ''}`}>
      <div className="setting-info">
        <div className="setting-key">{setting.key}</div>
        <div className="setting-desc">{setting.description}</div>
      </div>
      <div className="setting-controls">
        {renderInput()}
        <span className={`source-badge ${setting.source}`}>
          {setting.source === 'db' ? 'DB' : 'ENV'}
        </span>
        {setting.source === 'db' && (
          <button
            className="icon-btn reset"
            title={`Reset to env default: ${setting.env_value}`}
            onClick={handleReset}
            disabled={saveState === 'saving'}
          >
            <RotateCcw size={14} />
          </button>
        )}
        <button
          className={`icon-btn save ${!isDirty ? 'hidden' : ''} ${saveState}`}
          onClick={handleSave}
          disabled={!isDirty || saveState === 'saving'}
          title="Save"
        >
          {saveState === 'ok'  ? <CheckCircle size={14} /> :
           saveState === 'err' ? <AlertCircle size={14} /> :
           <Save size={14} />}
        </button>
      </div>
    </div>
  );
}

function CategoryCard({
  category,
  settings,
}: {
  category: string;
  settings: EffectiveSetting[];
}) {
  const meta = CATEGORY_META[category] ?? { label: category, icon: <Settings2 size={18} />, color: 'gray' };
  return (
    <div className="settings-card serpent-card">
      <div className={`card-header color-${meta.color}`}>
        {meta.icon}
        <h3>{meta.label}</h3>
        <span className="setting-count">{settings.length} settings</span>
      </div>
      <div className="settings-list">
        {settings.map(s => (
          <SettingRow key={s.key} setting={s} />
        ))}
      </div>
    </div>
  );
}

interface EmbeddingsStats {
  total_messages: number;
  messages_with_embeddings: number;
  messages_needing_embeddings: number;
  total_embeddings: number;
  progress_percent: number;
}

function TelegramAuthManager() {
  const [telegramPhone, setTelegramPhone] = useState('');
  const [telegramCode, setTelegramCode] = useState('');
  const [telegramPassword, setTelegramPassword] = useState('');
  const [telegramStep, setTelegramStep] = useState<'phone' | 'code' | 'password'>('phone');
  const [telegramPhoneHash, setTelegramPhoneHash] = useState('');
  const [telegramLoading, setTelegramLoading] = useState(false);
  const [telegramAuthorized, setTelegramAuthorized] = useState<boolean | null>(null);
  const [tgFolders, setTgFolders] = useState<any[]>([]);
  const { data: telegramUser } = useSWR(telegramAuthorized ? '/api/telegram/user' : null, fetcher);

  const checkTelegramAuth = async () => {
    try {
      const res = await api.get('/api/telegram/auth/status');
      setTelegramAuthorized(res.data.authorized);
    } catch (err) {
      setTelegramAuthorized(false);
    }
  };

  React.useEffect(() => {
    checkTelegramAuth();
  }, []);

  React.useEffect(() => {
    if (telegramAuthorized === true && tgFolders.length === 0) {
      const loadFolders = async () => {
        try {
          const res = await api.get('/api/telegram/folders');
          setTgFolders(res.data.folders || []);
        } catch (err) {
          console.error('Failed to load Telegram folders:', err);
        }
      };
      loadFolders();
    }
  }, [telegramAuthorized]);

  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setTelegramLoading(true);
    try {
      const res = await api.post('/api/telegram/auth/send_code', { phone: telegramPhone });
      setTelegramPhoneHash(res.data.phone_code_hash);
      setTelegramStep('code');
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || 'Failed to send code'));
    } finally {
      setTelegramLoading(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setTelegramLoading(true);
    try {
      const res = await api.post('/api/telegram/auth/verify', {
        phone: telegramPhone,
        code: telegramCode,
        phone_code_hash: telegramPhoneHash,
      });
      if (res.data.status === 'requires_2fa') {
        setTelegramStep('password');
      } else {
        setTelegramAuthorized(true);
        setTelegramPhone('');
        setTelegramCode('');
      }
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || 'Verification failed'));
    } finally {
      setTelegramLoading(false);
    }
  };

  const handleVerify2FA = async (e: React.FormEvent) => {
    e.preventDefault();
    setTelegramLoading(true);
    try {
      await api.post('/api/telegram/auth/2fa', { password: telegramPassword });
      setTelegramAuthorized(true);
      setTelegramPhone('');
      setTelegramCode('');
      setTelegramPassword('');
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || '2FA failed'));
    } finally {
      setTelegramLoading(false);
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Disconnect Telegram? You can login again anytime.')) return;
    setTelegramLoading(true);
    try {
      await api.post('/api/telegram/auth/logout');
      setTelegramAuthorized(false);
      setTelegramStep('phone');
      setTelegramPhone('');
      setTelegramCode('');
      setTelegramPassword('');
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || 'Logout failed'));
    } finally {
      setTelegramLoading(false);
    }
  };

  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(6, 78, 59, 0.1))',
      border: '1px solid rgba(16, 185, 129, 0.2)',
      borderRadius: '12px',
      padding: '20px',
      marginBottom: '24px'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <Phone size={20} style={{ color: '#10b981' }} />
        <h3 style={{ color: '#f8fafc', margin: 0, fontSize: '16px' }}>Авторизация Telegram</h3>
      </div>

      {telegramAuthorized === true ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '12px',
            background: 'rgba(16, 185, 129, 0.1)',
            borderRadius: '8px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>✅</span>
              <div>
                <p style={{ color: '#10b981', margin: '0', fontWeight: 'bold', fontSize: '14px' }}>Подключено</p>
                <p style={{ color: '#64748b', margin: '2px 0 0', fontSize: '11px' }}>Сеанс активен</p>
              </div>
            </div>
            <button
              onClick={handleDisconnect}
              disabled={telegramLoading}
              style={{
                padding: '6px 12px',
                background: 'rgba(239, 68, 68, 0.1)',
                color: '#fca5a5',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '4px',
                cursor: telegramLoading ? 'not-allowed' : 'pointer',
                fontSize: '12px',
                fontWeight: 'bold'
              }}
            >
              {telegramLoading ? 'Обработка...' : 'Отключить'}
            </button>
          </div>

          {telegramUser ? (
            <div style={{
              background: 'rgba(59, 130, 246, 0.05)',
              border: '1px solid rgba(59, 130, 246, 0.2)',
              borderRadius: '8px',
              padding: '16px',
              display: 'flex',
              gap: '16px',
              alignItems: 'flex-start'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                background: telegramUser.photo_url
                  ? `url(${telegramUser.photo_url})`
                  : 'linear-gradient(135deg, #3b82f6, #2563eb)',
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                flexShrink: 0
              }}>
                {!telegramUser.photo_url && (
                  <User size={28} style={{ color: '#fff' }} />
                )}
              </div>

              <div style={{ flex: 1 }}>
                <div style={{ marginBottom: '12px' }}>
                  <p style={{ color: '#94a3b8', margin: '0', fontSize: '11px', textTransform: 'uppercase', fontWeight: '600' }}>Номер телефона</p>
                  <p style={{ color: '#f8fafc', margin: '6px 0 0', fontSize: '14px', fontWeight: '600', fontFamily: 'monospace' }}>
                    {telegramUser.phone || '—'}
                  </p>
                </div>
                <div>
                  <p style={{ color: '#94a3b8', margin: '0', fontSize: '11px', textTransform: 'uppercase', fontWeight: '600' }}>Аккаунт</p>
                  <p style={{ color: '#cbd5e1', margin: '6px 0 0', fontSize: '13px' }}>
                    {telegramUser.first_name || ''} {telegramUser.last_name || ''}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div style={{
              background: 'rgba(59, 130, 246, 0.05)',
              border: '1px solid rgba(59, 130, 246, 0.2)',
              borderRadius: '8px',
              padding: '16px',
              color: '#64748b',
              textAlign: 'center',
              fontSize: '13px'
            }}>
              Загрузка информации профиля...
            </div>
          )}

          {tgFolders.length > 0 && (
            <div style={{
              background: 'rgba(168, 85, 247, 0.05)',
              border: '1px solid rgba(168, 85, 247, 0.2)',
              borderRadius: '8px',
              padding: '16px'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '12px'
              }}>
                <FolderPlus size={16} style={{ color: '#a855f7' }} />
                <p style={{ color: '#f8fafc', margin: 0, fontSize: '14px', fontWeight: '600' }}>Папки Telegram</p>
              </div>
              <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '8px'
              }}>
                {tgFolders.map((folder: any) => (
                  <div
                    key={folder.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '6px 12px',
                      background: 'rgba(168, 85, 247, 0.1)',
                      border: '1px solid rgba(168, 85, 247, 0.3)',
                      borderRadius: '6px',
                      color: '#c084fc',
                      fontSize: '12px'
                    }}
                  >
                    <Folder size={13} />
                    <span>{folder.name}</span>
                    <span style={{
                      padding: '0 4px',
                      background: 'rgba(168, 85, 247, 0.2)',
                      borderRadius: '4px',
                      fontSize: '11px'
                    }}>
                      {folder.channel_count || 0}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : telegramAuthorized === null ? (
        <div style={{ color: '#cbd5e1', textAlign: 'center', padding: '16px', fontSize: '14px' }}>
          Проверка...
        </div>
      ) : (
        <form onSubmit={
          telegramStep === 'phone' ? handleSendCode :
          telegramStep === 'code' ? handleVerifyCode :
          handleVerify2FA
        } style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div>
            {telegramStep === 'phone' && (
              <>
                <label style={{ color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase' }}>Номер телефона</label>
                <input
                  type="tel"
                  placeholder="+38123456789"
                  value={telegramPhone}
                  onChange={(e) => setTelegramPhone(e.target.value)}
                  disabled={telegramLoading}
                  autoFocus
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    marginTop: '6px',
                    background: 'rgba(15, 23, 42, 0.6)',
                    border: '1px solid rgba(16, 185, 129, 0.2)',
                    color: '#f8fafc',
                    borderRadius: '6px',
                    fontSize: '13px',
                    boxSizing: 'border-box'
                  }}
                />
              </>
            )}
            {telegramStep === 'code' && (
              <>
                <label style={{ color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase' }}>Код</label>
                <input
                  type="text"
                  placeholder="123456"
                  value={telegramCode}
                  onChange={(e) => setTelegramCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  disabled={telegramLoading}
                  autoFocus
                  maxLength={6}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    marginTop: '6px',
                    background: 'rgba(15, 23, 42, 0.6)',
                    border: '1px solid rgba(16, 185, 129, 0.2)',
                    color: '#f8fafc',
                    borderRadius: '6px',
                    fontSize: '13px',
                    boxSizing: 'border-box',
                    letterSpacing: '4px'
                  }}
                />
              </>
            )}
            {telegramStep === 'password' && (
              <>
                <label style={{ color: '#94a3b8', fontSize: '11px', textTransform: 'uppercase' }}>Пароль 2FA</label>
                <input
                  type="password"
                  placeholder="Ваш пароль"
                  value={telegramPassword}
                  onChange={(e) => setTelegramPassword(e.target.value)}
                  disabled={telegramLoading}
                  autoFocus
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    marginTop: '6px',
                    background: 'rgba(15, 23, 42, 0.6)',
                    border: '1px solid rgba(16, 185, 129, 0.2)',
                    color: '#f8fafc',
                    borderRadius: '6px',
                    fontSize: '13px',
                    boxSizing: 'border-box'
                  }}
                />
              </>
            )}
          </div>
          <button
            type="submit"
            disabled={telegramLoading}
            style={{
              padding: '10px 16px',
              background: telegramLoading ? 'rgba(16, 185, 129, 0.5)' : 'linear-gradient(135deg, #10b981, #059669)',
              color: '#f8fafc',
              border: 'none',
              borderRadius: '6px',
              fontWeight: '600',
              cursor: telegramLoading ? 'not-allowed' : 'pointer',
              fontSize: '13px'
            }}
          >
            {telegramLoading ? '⏳ Обработка...' : `Продолжить →`}
          </button>
        </form>
      )}
    </div>
  );
}

function EmbeddingsManager() {
  const { data: stats, mutate: mutateStats } = useSWR<EmbeddingsStats>('/api/stats/embeddings', fetcher);
  const [reindexing, setReindexing] = useState(false);
  const [reindexStatus, setReindexStatus] = useState<'idle' | 'queued' | 'success' | 'error'>('idle');

  const handleReindex = async () => {
    setReindexing(true);
    setReindexStatus('queued');
    try {
      await api.post('/api/stats/embeddings/reindex');
      setReindexStatus('success');
      await mutateStats();
      setTimeout(() => setReindexStatus('idle'), 3000);
    } catch (err) {
      setReindexStatus('error');
      console.error('Reindex failed:', err);
      setTimeout(() => setReindexStatus('idle'), 3000);
    } finally {
      setReindexing(false);
    }
  };

  if (!stats) return <div className="loading">Загрузка...</div>;

  return (
    <div className="embeddings-manager serpent-card">
      <div className="embeddings-header">
        <div>
          <h3>🤖 Управление Embeddings</h3>
          <p className="text-secondary">Переиндексируйте embeddings для улучшения качества поиска</p>
        </div>
        <button
          className={`btn-reindex ${reindexStatus}`}
          onClick={handleReindex}
          disabled={reindexing}
          title="Перегенерировать все embeddings для лучшего поиска"
        >
          <RefreshCw size={18} />
          {reindexing ? 'Переиндексируется...' : 'Переиндексировать'}
        </button>
      </div>

      <div className="embeddings-stats">
        <div className="stat">
          <span className="label">Всего сообщений:</span>
          <span className="value">{stats.total_messages}</span>
        </div>
        <div className="stat">
          <span className="label">С embeddings:</span>
          <span className="value">{stats.messages_with_embeddings}</span>
        </div>
        <div className="stat">
          <span className="label">Нужны embeddings:</span>
          <span className="value">{stats.messages_needing_embeddings}</span>
        </div>
        <div className="stat">
          <span className="label">Прогресс:</span>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${stats.progress_percent}%` }}></div>
            <span className="progress-text">{stats.progress_percent.toFixed(1)}%</span>
          </div>
        </div>
      </div>

      {reindexStatus === 'success' && <div className="status-msg success">✓ Переиндексировка запущена!</div>}
      {reindexStatus === 'error' && <div className="status-msg error">✗ Ошибка при переиндексировке</div>}
    </div>
  );
}

const Settings: React.FC = () => {
  const { data, error } = useSWR<SettingsResponse>(EFFECTIVE_URL, fetcher);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  const grouped = useCallback(() => {
    if (!data) return {} as Record<string, EffectiveSetting[]>;
    return data.settings.reduce<Record<string, EffectiveSetting[]>>((acc, s) => {
      (acc[s.category] ??= []).push(s);
      return acc;
    }, {});
  }, [data])();

  const categories = CATEGORY_ORDER.filter(c => c in grouped);
  const displayed = activeCategory ? [activeCategory] : categories;

  if (error) return <div className="error">Не удалось загрузить настройки</div>;
  if (!data)  return <div className="loading">Загрузка настроек...</div>;

  const dbCount = data.settings.filter(s => s.source === 'db').length;

  return (
    <div className="settings-page">
      <div className="page-header">
        <h1 className="text-gradient">Настройки</h1>
        <p className="text-secondary">
          Конфигурация системы — значения из БД переопределяют .env
          {dbCount > 0 && <span className="db-overrides-badge">{dbCount} DB overrides</span>}
        </p>
      </div>

      <TelegramAuthManager />

      <EmbeddingsManager />

      <div className="category-tabs">
        <button
          className={`cat-tab ${activeCategory === null ? 'active' : ''}`}
          onClick={() => setActiveCategory(null)}
        >
          Все
        </button>
        {categories.map(cat => {
          const meta = CATEGORY_META[cat];
          return (
            <button
              key={cat}
              className={`cat-tab ${activeCategory === cat ? 'active' : ''} color-${meta.color}`}
              onClick={() => setActiveCategory(cat === activeCategory ? null : cat)}
            >
              {meta.icon}
              {meta.label}
            </button>
          );
        })}
      </div>

      <div className="settings-grid">
        {displayed.map(cat => (
          <CategoryCard key={cat} category={cat} settings={grouped[cat] ?? []} />
        ))}
      </div>
    </div>
  );
};

export default Settings;
