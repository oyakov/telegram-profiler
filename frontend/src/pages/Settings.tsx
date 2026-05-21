import React, { useState, useMemo, useRef, useEffect } from 'react';
import useSWR, { mutate } from 'swr';
import api, { fetcher } from '../services/api';
import {
  Settings2, Cpu, Database, Mic, Monitor, RotateCcw, Save,
  CheckCircle, AlertCircle, Share2, TrendingUp,
} from 'lucide-react';
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

const CATEGORY_META: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  llm:        { label: 'AI / LLM',    icon: <Cpu size={18} />,        color: 'purple' },
  embeddings: { label: 'Embeddings',  icon: <Database size={18} />,   color: 'blue'   },
  whisper:    { label: 'Whisper STT', icon: <Mic size={18} />,        color: 'green'  },
  telegram:   { label: 'Telegram',    icon: <Share2 size={18} />,     color: 'orange' },
  system:     { label: 'Система',     icon: <Monitor size={18} />,    color: 'yellow' },
  heuristics: { label: 'Эвристики',   icon: <TrendingUp size={18} />, color: 'red'    },
};

const CATEGORY_ORDER = ['llm', 'heuristics', 'embeddings', 'whisper', 'telegram', 'system'];

type SaveState = 'idle' | 'saving' | 'ok' | 'err';

function SettingRow({ setting }: { setting: EffectiveSetting }) {
  const [localValue, setLocalValue] = useState<string>(String(setting.value ?? ''));
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const serverValueRef = useRef(String(setting.value ?? ''));
  const isDirty = localValue !== serverValueRef.current;

  // Sync to new server value when SWR revalidates, but only if user hasn't edited
  useEffect(() => {
    const newServerVal = String(setting.value ?? '');
    if (localValue === serverValueRef.current) {
      setLocalValue(newServerVal);
    }
    serverValueRef.current = newServerVal;
  }, [setting.value]); // eslint-disable-line react-hooks/exhaustive-deps

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
            title={`Сбросить до значения .env: ${setting.env_value}`}
            onClick={handleReset}
            disabled={saveState === 'saving'}
            aria-label="Сбросить к значению .env"
          >
            <RotateCcw size={14} />
          </button>
        )}
        <button
          className={`icon-btn save ${!isDirty ? 'hidden' : ''} ${saveState}`}
          onClick={handleSave}
          disabled={!isDirty || saveState === 'saving'}
          title="Сохранить"
          aria-label="Сохранить изменение"
        >
          {saveState === 'ok'  ? <CheckCircle size={14} /> :
           saveState === 'err' ? <AlertCircle size={14} /> :
           <Save size={14} />}
        </button>
      </div>
    </div>
  );
}

function CategoryCard({ category, settings }: { category: string; settings: EffectiveSetting[] }) {
  const meta = CATEGORY_META[category] ?? { label: category, icon: <Settings2 size={18} />, color: 'gray' };
  return (
    <div className="settings-card serpent-card no-hover">
      <div className={`card-header color-${meta.color}`}>
        {meta.icon}
        <h3>{meta.label}</h3>
        <span className="setting-count">{settings.length} параметров</span>
      </div>
      <div className="settings-list">
        {settings.map(s => <SettingRow key={s.key} setting={s} />)}
      </div>
    </div>
  );
}

const Settings: React.FC = () => {
  const { data, error } = useSWR<SettingsResponse>(EFFECTIVE_URL, fetcher);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  const isLoading = !data && !error;

  const grouped = useMemo(() => {
    if (!data) return {} as Record<string, EffectiveSetting[]>;
    return data.settings.reduce<Record<string, EffectiveSetting[]>>((acc, s) => {
      (acc[s.category] ??= []).push(s);
      return acc;
    }, {});
  }, [data]);

  const categories = CATEGORY_ORDER.filter(c => c in grouped);
  const displayed = activeCategory ? [activeCategory] : categories;

  if (error) return <div className="error">Не удалось загрузить настройки</div>;

  const dbCount = data?.settings ? data.settings.filter(s => s.source === 'db').length : 0;

  return (
    <div className="settings-page">
      <div className="page-header">
        <h1 className="text-gradient">Настройки</h1>
        {isLoading ? (
          <div className="skeleton-placeholder text-skeleton" style={{ width: '380px', marginTop: '6px' }} />
        ) : (
          <p className="text-secondary">
            Конфигурация systems — значения из БД переопределяют .env
            {dbCount > 0 && <span className="db-overrides-badge">{dbCount} переопределено</span>}
          </p>
        )}
      </div>

      <div className="category-tabs">
        <button
          className={`cat-tab ${activeCategory === null ? 'active' : ''}`}
          onClick={() => setActiveCategory(null)}
          disabled={isLoading}
        >
          Все
        </button>
        {!isLoading && categories.map(cat => {
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
        {isLoading ? (
          CATEGORY_ORDER.slice(0, 3).map((cat, index) => {
            const meta = CATEGORY_META[cat];
            return (
              <div key={`settings-card-skeleton-${index}`} className="settings-card serpent-card no-hover" style={{ position: 'relative', overflow: 'hidden' }}>
                <div className="card-loading-bar" />
                <div className={`card-header color-${meta.color}`} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', display: 'flex', alignItems: 'center', gap: '10px', padding: '16px' }}>
                  {meta.icon}
                  <h3 style={{ margin: 0, flex: 1 }}>{meta.label}</h3>
                  <div className="skeleton-placeholder" style={{ width: '80px', height: '18px', borderRadius: '4px' }} />
                </div>
                <div className="settings-list" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {Array.from({ length: 3 }).map((_, rIdx) => (
                    <div key={rIdx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: rIdx < 2 ? '16px' : '0', borderBottom: rIdx < 2 ? '1px solid rgba(255, 255, 255, 0.05)' : 'none' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        <div className="skeleton-placeholder text-skeleton" style={{ width: '140px' }} />
                        <div className="skeleton-placeholder text-skeleton" style={{ width: '220px', height: '0.75rem' }} />
                      </div>
                      <div className="skeleton-placeholder" style={{ width: '70px', height: '32px', borderRadius: '6px' }} />
                    </div>
                  ))}
                </div>
              </div>
            );
          })
        ) : (
          displayed.map(cat => (
            <CategoryCard key={cat} category={cat} settings={grouped[cat] ?? []} />
          ))
        )}
      </div>
    </div>
  );
};

export default Settings;
