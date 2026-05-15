import React, { useState } from 'react';
import { Plus, X, TrendingUp, Save, Loader } from 'lucide-react';
import type { LeadProfile } from '../../hooks/useLeads';

interface Props {
  profile: LeadProfile;
  updateProfileField: (field: keyof LeadProfile, value: string | number | string[]) => void;
  addTag: (field: 'keywords' | 'interests', value: string) => void;
  removeTag: (field: 'keywords' | 'interests', index: number) => void;
  handleSearch: () => void;
  isSearching: boolean;
  onSaveClick: () => void;
}

const LeadProfileConstructor: React.FC<Props> = ({
  profile,
  updateProfileField,
  addTag,
  removeTag,
  handleSearch,
  isSearching,
  onSaveClick,
}) => {
  const [currentKeywordInput, setCurrentKeywordInput] = useState('');
  const [currentInterestInput, setCurrentInterestInput] = useState('');

  const handleAddKeyword = () => {
    if (currentKeywordInput) {
      addTag('keywords', currentKeywordInput);
      setCurrentKeywordInput('');
    }
  };

  const handleAddInterest = () => {
    if (currentInterestInput) {
      addTag('interests', currentInterestInput);
      setCurrentInterestInput('');
    }
  };

  return (
    <div className="lead-constructor">
      <h2>Конструктор Профиля Лида</h2>

      <div className="form-section">
        <label>Контактные данные</label>
        <div className="form-row">
          <input
            type="text"
            placeholder="Имя"
            value={profile.first_name}
            onChange={(e) => updateProfileField('first_name', e.target.value)}
            className="form-input"
          />
          <input
            type="text"
            placeholder="Фамилия"
            value={profile.last_name}
            onChange={(e) => updateProfileField('last_name', e.target.value)}
            className="form-input"
          />
        </div>

        <div className="form-row">
          <input
            type="text"
            placeholder="Компания"
            value={profile.company}
            onChange={(e) => updateProfileField('company', e.target.value)}
            className="form-input"
          />
          <input
            type="text"
            placeholder="Должность"
            value={profile.position}
            onChange={(e) => updateProfileField('position', e.target.value)}
            className="form-input"
          />
        </div>
      </div>

      <div className="form-section">
        <label>Ключевые слова</label>
        <div className="keyword-input-row">
          <input
            type="text"
            placeholder="Добавить ключевое слово..."
            value={currentKeywordInput}
            onChange={(e) => setCurrentKeywordInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAddKeyword()}
            className="form-input"
          />
          <button onClick={handleAddKeyword} className="btn-small primary">
            <Plus size={16} />
          </button>
        </div>
        <div className="tags-container">
          {profile.keywords.map((kw, idx) => (
            <span key={idx} className="tag">
              {kw}
              <button onClick={() => removeTag('keywords', idx)} className="tag-remove">
                <X size={14} />
              </button>
            </span>
          ))}
        </div>
      </div>

      <div className="form-section">
        <label>Интересы</label>
        <div className="keyword-input-row">
          <input
            type="text"
            placeholder="Добавить интерес..."
            value={currentInterestInput}
            onChange={(e) => setCurrentInterestInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleAddInterest()}
            className="form-input"
          />
          <button onClick={handleAddInterest} className="btn-small primary">
            <Plus size={16} />
          </button>
        </div>
        <div className="tags-container">
          {profile.interests.map((int, idx) => (
            <span key={idx} className="tag interest-tag">
              {int}
              <button onClick={() => removeTag('interests', idx)} className="tag-remove">
                <X size={14} />
              </button>
            </span>
          ))}
        </div>
      </div>

      <div className="form-section">
        <label>Фильтры поиска</label>
        <div className="form-group">
          <label className="filter-label">
            Минимальный Score: <span className="value">{profile.min_score}</span>
          </label>
          <input
            type="range"
            min="0"
            max="100"
            step="5"
            value={profile.min_score}
            onChange={(e) => updateProfileField('min_score', parseFloat(e.target.value))}
            className="form-range"
          />
        </div>

        <div className="form-group">
          <label className="filter-label">
            Активность в канале: {profile.min_activity_ratio}% - {profile.max_activity_ratio}%
          </label>
          <div className="range-inputs">
            <input
              type="number"
              min="0"
              max="100"
              value={profile.min_activity_ratio}
              onChange={(e) => updateProfileField('min_activity_ratio', parseFloat(e.target.value))}
              className="form-input small"
            />
            <input
              type="number"
              min="0"
              max="100"
              value={profile.max_activity_ratio}
              onChange={(e) => updateProfileField('max_activity_ratio', parseFloat(e.target.value))}
              className="form-input small"
            />
          </div>
        </div>
      </div>

      <div className="form-actions">
        <button className="btn-venom primary" onClick={handleSearch} disabled={isSearching}>
          {isSearching ? (
            <><Loader size={18} className="spinner" /> Поиск...</>
          ) : (
            <><TrendingUp size={18} /> Искать лидов</>
          )}
        </button>

        <button className="btn-venom secondary" onClick={onSaveClick} disabled={isSearching}>
          <Save size={18} /> Сохранить поиск
        </button>
      </div>
    </div>
  );
};

export default LeadProfileConstructor;
