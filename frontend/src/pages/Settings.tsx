import React, { useState, useCallback } from 'react';
import useSWR, { mutate } from 'swr';
import api from '../services/api';
import { Settings2, Cpu, Database, Mic, Monitor, RotateCcw, Save, CheckCircle, AlertCircle } from 'lucide-react';
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
