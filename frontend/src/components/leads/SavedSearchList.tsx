import React from 'react';
import { History, TrashIcon } from 'lucide-react';
import type { LeadSearch } from '../../hooks/useLeads';

interface Props {
  savedSearches?: LeadSearch[] | null;
  isLoading: boolean;
  onRun: (id: string) => void;
  onDelete: (id: string) => void;
  isSearching: boolean;
}

const SavedSearchList: React.FC<Props> = ({ savedSearches, isLoading, onRun, onDelete, isSearching }) => {
  if (isLoading) {
    return (
      <div className="saved-searches-section">
        <div className="card-loading-bar" />
        <h3>Сохранённые поиски</h3>
        <div className="saved-searches-list">
          {[1, 2, 3].map((i) => (
            <div key={i} className="saved-search-item" style={{ pointerEvents: 'none' }}>
              <div className="search-info" style={{ width: '80%' }}>
                <div className="skeleton-placeholder text-skeleton" style={{ width: '40%', height: '14px', marginBottom: '8px' }} />
                <div className="skeleton-placeholder text-skeleton" style={{ width: '70%', height: '12px', marginBottom: '8px' }} />
                <div className="skeleton-placeholder count-skeleton" style={{ width: '30%', height: '10px' }} />
              </div>
              <div className="search-actions">
                <div className="skeleton-placeholder" style={{ width: '28px', height: '28px', borderRadius: '8px' }} />
                <div className="skeleton-placeholder" style={{ width: '28px', height: '28px', borderRadius: '8px' }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!savedSearches || savedSearches.length === 0) return null;

  return (
    <div className="saved-searches-section">
      <h3>Сохранённые поиски</h3>
      <div className="saved-searches-list">
        {savedSearches.map((search) => (
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
                onClick={() => onRun(search.id)}
                disabled={isSearching}
                title="Запустить поиск"
              >
                <History size={14} />
              </button>
              <button
                className="btn-small danger"
                onClick={() => onDelete(search.id)}
                title="Удалить поиск"
              >
                <TrashIcon size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SavedSearchList;
