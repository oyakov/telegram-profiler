import React, { useState } from 'react';
import api from '../services/api';
import { Search as SearchIcon, Sparkles, User, Clock, ArrowRight, AlertCircle } from 'lucide-react';
import './Search.css';

interface Evidence {
  text: string;
  relevance?: number;
}

interface SearchContact {
  id: string;
  first_name?: string;
  last_name?: string;
  telegram_username?: string;
  similarity: number;
  search_type?: string;
  evidence?: Evidence[];
}

interface SearchMessage {
  id?: string;
  contact_name?: string;
  group_name?: string;
  timestamp: string;
  content: string;
  similarity?: number;
}

interface SearchResults {
  contacts: SearchContact[];
  messages: SearchMessage[];
}

const Search: React.FC = () => {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<SearchResults | null>(null);
  const [activeTab, setActiveTab] = useState<'ai' | 'keyword'>('ai');
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    setError(null);
    setResults(null);
    try {
      if (activeTab === 'ai') {
        const res = await api.post('/api/search', { query, limit: 15 });
        setResults(res.data);
      } else {
        const res = await api.get('/api/messages/search', { params: { query, page_size: 50 } });
        setResults({ contacts: [], messages: res.data.messages || [] });
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка поиска. Попробуйте ещё раз.');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="search-page">
      <div className="page-header">
        <div>
          <h1 className="text-gradient">Интеллектуальный поиск</h1>
          <p className="text-secondary">Найдите нужные связи и сообщения с помощью AI</p>
        </div>
      </div>

      <div className="search-tabs">
        <button
          className={`tab-btn ${activeTab === 'ai' ? 'active' : ''}`}
          onClick={() => setActiveTab('ai')}
        >
          <Sparkles size={18} />
          Семантический (AI)
        </button>
        <button
          className={`tab-btn ${activeTab === 'keyword' ? 'active' : ''}`}
          onClick={() => setActiveTab('keyword')}
        >
          <SearchIcon size={18} />
          По словам
        </button>
      </div>

      <form className="search-container serpent-card" onSubmit={handleSearch}>
        <input
          type="text"
          placeholder={activeTab === 'ai'
            ? "Например: «кто занимается недвижимостью в Белграде?»"
            : "Введите ключевое слово..."}
          value={query}
          onChange={e => setQuery(e.target.value)}
          disabled={isSearching}
        />
        <button type="submit" className="search-submit" disabled={isSearching}>
          {isSearching ? <div className="loader" /> : <ArrowRight size={24} />}
        </button>
      </form>

      {isSearching && (
        <div className="thinking-container">
          <Sparkles className="sparkle-anim" />
          <span>AI анализирует смыслы и связи...</span>
        </div>
      )}

      {error && (
        <div className="search-error">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {results && !isSearching && (
        <div className="results-grid">
          {results.contacts.length > 0 && (
            <div className="results-column">
              <h3>👥 Найденные люди</h3>
              <div className="results-list">
                {results.contacts.map(c => (
                  <div key={c.id} className="result-card serpent-card contact-card">
                    <div className="contact-avatar">
                      <User size={20} />
                    </div>
                    <div className="contact-details">
                      <div className="name-score">
                        <strong>{c.first_name} {c.last_name || ''}</strong>
                        <span className="similarity">{(c.similarity * 100).toFixed(0)}%</span>
                      </div>
                      <span className="username">@{c.telegram_username || 'Н/Д'}</span>
                      <div className="similarity-bar">
                        <div className="bar-fill" style={{ width: `${c.similarity * 100}%` }} />
                      </div>

                      {c.search_type && (
                        <div className="search-type-badge">
                          {c.search_type === 'semantic' ? '🤖 Семантический' : '🔤 Ключевые слова'}
                        </div>
                      )}

                      {c.evidence && c.evidence.length > 0 && (
                        <div className="evidence-section">
                          <div className="evidence-header">Почему выбран:</div>
                          <div className="evidence-quotes">
                            {c.evidence.map((quote, idx) => (
                              <div key={idx} className="evidence-quote">
                                <p>{quote.text}</p>
                                {quote.relevance != null && (
                                  <span className="evidence-relevance">
                                    {(quote.relevance * 100).toFixed(0)}% совпадение
                                  </span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {results.messages.length > 0 && (
            <div className="results-column">
              <h3>💬 Релевантные сообщения</h3>
              <div className="results-list">
                {results.messages.map((m, idx) => (
                  <div key={m.id ?? idx} className="result-card glass message-card">
                    <div className="message-header">
                      <div className="author">
                        <strong>{m.contact_name}</strong>
                        <span className="group">в {m.group_name}</span>
                      </div>
                      <div className="time">
                        <Clock size={12} />
                        {new Date(m.timestamp).toLocaleString('ru', {
                          hour: '2-digit', minute: '2-digit',
                        })}
                      </div>
                    </div>
                    <p className="message-content">{m.content}</p>
                    {m.similarity != null && (
                      <div className="message-footer">
                        <span className="score">Релевантность: {m.similarity.toFixed(2)}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {results.contacts.length === 0 && results.messages.length === 0 && (
            <div className="no-results text-secondary">
              Ничего не найдено по вашему запросу.
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Search;
