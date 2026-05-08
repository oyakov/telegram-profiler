import React, { useState } from 'react';
import useSWR from 'swr';
import api from '../services/api';
import {
  TrendingUp,
  DollarSign,
  MessageSquare,
  ExternalLink,
  X,
  Plus,
  Save,
  Loader,
  History,
  TrashIcon,
} from 'lucide-react';
import './Leads.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

interface LeadProfile {
  first_name: string;
  last_name: string;
  company: string;
  position: string;
  keywords: string[];
  interests: string[];
  skills: string[];
  email: string;
  phone: string;
  min_score: number;
  min_activity_ratio: number;
  max_activity_ratio: number;
  created_after?: string;
  created_before?: string;
}

interface LeadSearch {
  id: string;
  name: string;
  description?: string;
  profile_filter: LeadProfile;
  is_active: boolean;
  result_count: number;
  last_run_at?: string;
  created_at: string;
  updated_at: string;
}

interface Contact {
  id: string;
  first_name: string;
  last_name: string;
  telegram_username?: string;
  lead_score: number;
  our_channel_ratio: number;
  company?: string;
  position?: string;
  interests?: string[];
}

const Leads: React.FC = () => {
  const [profile, setProfile] = useState<LeadProfile>({
    first_name: '',
    last_name: '',
    company: '',
    position: '',
    keywords: [],
    interests: [],
    skills: [],
    email: '',
    phone: '',
    min_score: 10,
    min_activity_ratio: 0,
    max_activity_ratio: 100,
  });

  const [searchResults, setSearchResults] = useState<any>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [savingSearch, setSavingSearch] = useState(false);
  const [searchName, setSearchName] = useState('');
  const [searchDescription, setSearchDescription] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);

  const [currentKeywordInput, setCurrentKeywordInput] = useState('');
  const [currentInterestInput, setCurrentInterestInput] = useState('');

  // Saved searches
  const { data: savedSearches, mutate: mutateSavedSearches } = useSWR(
    '/api/leads/searches?active_only=true',
    fetcher
  );

  const handleAddKeyword = () => {
    if (currentKeywordInput.trim()) {
      setProfile(prev => ({
        ...prev,
        keywords: [...prev.keywords, currentKeywordInput.trim()]
      }));
      setCurrentKeywordInput('');
    }
  };

  const handleRemoveKeyword = (index: number) => {
    setProfile(prev => ({
      ...prev,
      keywords: prev.keywords.filter((_, i) => i !== index)
    }));
  };

  const handleAddInterest = () => {
    if (currentInterestInput.trim()) {
      setProfile(prev => ({
        ...prev,
        interests: [...prev.interests, currentInterestInput.trim()]
      }));
      setCurrentInterestInput('');
    }
  };

  const handleRemoveInterest = (index: number) => {
    setProfile(prev => ({
      ...prev,
      interests: prev.interests.filter((_, i) => i !== index)
    }));
  };

  const handleSearch = async () => {
    setIsSearching(true);
    try {
      const res = await api.post('/api/leads/search', {
        ...profile,
        page: 1,
        page_size: 50,
      });
      setSearchResults(res.data);
    } catch (err) {
      console.error('Search error:', err);
      alert('Failed to search leads');
    } finally {
      setIsSearching(false);
    }
  };

  const handleSaveSearch = async () => {
    if (!searchName.trim()) {
      alert('Please enter a search name');
      return;
    }

    setSavingSearch(true);
    try {
      await api.post('/api/leads/searches', {
        name: searchName,
        description: searchDescription,
        profile_filter: {
          ...profile,
          page: 1,
          page_size: 50,
        },
      });
      alert('Search saved successfully');
      setShowSaveDialog(false);
      setSearchName('');
      setSearchDescription('');
      mutateSavedSearches();
    } catch (err) {
      console.error('Save error:', err);
      alert('Failed to save search');
    } finally {
      setSavingSearch(false);
    }
  };

  const handleRunSavedSearch = async (searchId: string) => {
    setIsSearching(true);
    try {
      const res = await api.post(`/api/leads/searches/${searchId}/run`);
      setSearchResults(res.data);
    } catch (err) {
      console.error('Run search error:', err);
      alert('Failed to run search');
    } finally {
      setIsSearching(false);
    }
  };

  const handleDeleteSavedSearch = async (searchId: string) => {
    if (window.confirm('Delete this saved search?')) {
      try {
        await api.delete(`/api/leads/searches/${searchId}`);
        mutateSavedSearches();
      } catch (err) {
        console.error('Delete error:', err);
        alert('Failed to delete search');
      }
    }
  };

  return (
    <div className="leads-page">
      <div className="page-header-actions">
        <div>
          <h1 className="text-gradient">Поиск Лидов</h1>
          <p className="text-secondary">Конструктор профиля для целевого поиска среди выявленных лидов</p>
        </div>
      </div>

      <div className="leads-container">
        {/* Left: Lead Profile Constructor */}
        <div className="lead-constructor">
          <h2>Конструктор Профиля Лида</h2>

          <div className="form-section">
            <label>Контактные данные</label>
            <div className="form-row">
              <input
                type="text"
                placeholder="Имя"
                value={profile.first_name}
                onChange={(e) => setProfile(prev => ({ ...prev, first_name: e.target.value }))}
                className="form-input"
              />
              <input
                type="text"
                placeholder="Фамилия"
                value={profile.last_name}
                onChange={(e) => setProfile(prev => ({ ...prev, last_name: e.target.value }))}
                className="form-input"
              />
            </div>

            <div className="form-row">
              <input
                type="text"
                placeholder="Компания"
                value={profile.company}
                onChange={(e) => setProfile(prev => ({ ...prev, company: e.target.value }))}
                className="form-input"
              />
              <input
                type="text"
                placeholder="Должность"
                value={profile.position}
                onChange={(e) => setProfile(prev => ({ ...prev, position: e.target.value }))}
                className="form-input"
              />
            </div>

            <div className="form-row">
              <input
                type="email"
                placeholder="Email"
                value={profile.email}
                onChange={(e) => setProfile(prev => ({ ...prev, email: e.target.value }))}
                className="form-input"
              />
              <input
                type="tel"
                placeholder="Телефон"
                value={profile.phone}
                onChange={(e) => setProfile(prev => ({ ...prev, phone: e.target.value }))}
                className="form-input"
              />
            </div>
          </div>

          {/* Keywords */}
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
                  <button
                    onClick={() => handleRemoveKeyword(idx)}
                    className="tag-remove"
                  >
                    <X size={14} />
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Interests */}
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
                  <button
                    onClick={() => handleRemoveInterest(idx)}
                    className="tag-remove"
                  >
                    <X size={14} />
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Filters */}
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
                onChange={(e) => setProfile(prev => ({ ...prev, min_score: parseFloat(e.target.value) }))}
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
                  onChange={(e) => setProfile(prev => ({ ...prev, min_activity_ratio: parseFloat(e.target.value) }))}
                  className="form-input small"
                />
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={profile.max_activity_ratio}
                  onChange={(e) => setProfile(prev => ({ ...prev, max_activity_ratio: parseFloat(e.target.value) }))}
                  className="form-input small"
                />
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="form-actions">
            <button
              className="btn-venom primary"
              onClick={handleSearch}
              disabled={isSearching}
            >
              {isSearching ? (
                <>
                  <Loader size={18} className="spinner" />
                  Поиск...
                </>
              ) : (
                <>
                  <TrendingUp size={18} />
                  Искать лидов
                </>
              )}
            </button>

            <button
              className="btn-venom secondary"
              onClick={() => setShowSaveDialog(true)}
              disabled={isSearching}
            >
              <Save size={18} />
              Сохранить поиск
            </button>
          </div>
        </div>

        {/* Right: Results and Saved Searches */}
        <div className="results-panel">
          {/* Saved Searches */}
          {savedSearches && savedSearches.length > 0 && (
            <div className="saved-searches-section">
              <h3>Сохранённые поиски</h3>
              <div className="saved-searches-list">
                {savedSearches.map((search: LeadSearch) => (
                  <div key={search.id} className="saved-search-item">
                    <div className="search-info">
                      <h4>{search.name}</h4>
                      {search.description && <p>{search.description}</p>}
                      <span className="search-meta">
                        {search.result_count} результатов
                        {search.last_run_at && ` • Запуск: ${new Date(search.last_run_at).toLocaleDateString('ru-RU')}`}
                      </span>
                    </div>
                    <div className="search-actions">
                      <button
                        className="btn-small primary"
                        onClick={() => handleRunSavedSearch(search.id)}
                        disabled={isSearching}
                      >
                        <History size={14} />
                      </button>
                      <button
                        className="btn-small danger"
                        onClick={() => handleDeleteSavedSearch(search.id)}
                      >
                        <TrashIcon size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Search Results */}
          {searchResults && (
            <div className="search-results-section">
              <h3>
                Результаты поиска
                <span className="result-count">({searchResults.total})</span>
              </h3>

              {searchResults.contacts.length === 0 ? (
                <div className="no-results">По вашему запросу ничего не найдено</div>
              ) : (
                <div className="leads-grid">
                  {searchResults.contacts.map((contact: Contact) => (
                    <div key={contact.id} className="lead-card serpent-card">
                      <div className="lead-header">
                        <div className="lead-main">
                          <div className="lead-avatar">
                            <DollarSign size={20} />
                          </div>
                          <div>
                            <h4>{contact.first_name} {contact.last_name || ''}</h4>
                            <span className="username">@{contact.telegram_username || 'private'}</span>
                          </div>
                        </div>
                        <div className="lead-score-box">
                          <span className="label">Score</span>
                          <span className="value">{contact.lead_score}</span>
                        </div>
                      </div>

                      <div className="lead-details">
                        {contact.company && <p className="detail"><strong>Компания:</strong> {contact.company}</p>}
                        {contact.position && <p className="detail"><strong>Должность:</strong> {contact.position}</p>}
                      </div>

                      <div className="lead-stats">
                        <div className="stat-item">
                          <MessageSquare size={14} />
                          <span>Активность: {contact.our_channel_ratio}% в канале</span>
                        </div>
                      </div>

                      <div className="lead-footer">
                        <button className="btn-small secondary">История</button>
                        <a href={`https://t.me/${contact.telegram_username}`} target="_blank" rel="noreferrer" className="btn-small primary">
                          <ExternalLink size={14} />
                          Связаться
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {!searchResults && (
            <div className="empty-state">
              <TrendingUp size={48} />
              <p>Запустите поиск, чтобы увидеть результаты</p>
            </div>
          )}
        </div>
      </div>

      {/* Save Search Dialog */}
      {showSaveDialog && (
        <div className="modal-overlay" onClick={() => setShowSaveDialog(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Сохранить поиск</h3>
              <button
                className="modal-close"
                onClick={() => setShowSaveDialog(false)}
              >
                <X size={20} />
              </button>
            </div>

            <div className="modal-body">
              <div className="form-group">
                <label>Название</label>
                <input
                  type="text"
                  placeholder="Мой поиск лидов..."
                  value={searchName}
                  onChange={(e) => setSearchName(e.target.value)}
                  className="form-input"
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label>Описание (опционально)</label>
                <textarea
                  placeholder="Описание этого поиска..."
                  value={searchDescription}
                  onChange={(e) => setSearchDescription(e.target.value)}
                  className="form-textarea"
                  rows={3}
                />
              </div>
            </div>

            <div className="modal-footer">
              <button
                className="btn secondary"
                onClick={() => setShowSaveDialog(false)}
              >
                Отмена
              </button>
              <button
                className="btn primary"
                onClick={handleSaveSearch}
                disabled={savingSearch || !searchName.trim()}
              >
                {savingSearch ? 'Сохранение...' : 'Сохранить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Leads;
