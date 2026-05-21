import React from 'react';
import { TrendingUp } from 'lucide-react';
import LeadCard from './LeadCard';
import type { LeadSearchResult } from '../../hooks/useLeads';

interface Props {
  searchResults: LeadSearchResult | null;
  isSearching: boolean;
}

const LeadGrid: React.FC<Props> = ({ searchResults, isSearching }) => {
  if (isSearching) {
    return (
      <div className="search-results-section">
        <div className="card-loading-bar" />
        <h3>
          Результаты поиска
          <span className="result-count">(выполняется поиск...)</span>
        </h3>
        <div className="leads-grid">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="lead-card serpent-card" style={{ pointerEvents: 'none' }}>
              <div className="lead-header">
                <div className="lead-main" style={{ width: '70%' }}>
                  <div className="skeleton-placeholder" style={{ width: '44px', height: '44px', borderRadius: '12px', flexShrink: 0 }} />
                  <div style={{ width: '70%' }}>
                    <div className="skeleton-placeholder text-skeleton" style={{ width: '80%', height: '14px', marginBottom: '8px' }} />
                    <div className="skeleton-placeholder text-skeleton" style={{ width: '50%', height: '12px' }} />
                  </div>
                </div>
                <div className="lead-score-box" style={{ width: '60px', height: '46px', justifyContent: 'center' }}>
                  <div className="skeleton-placeholder text-skeleton" style={{ width: '30px', height: '8px', marginBottom: '6px' }} />
                  <div className="skeleton-placeholder text-skeleton" style={{ width: '20px', height: '14px' }} />
                </div>
              </div>

              <div className="lead-details" style={{ margin: '8px 0' }}>
                <div className="skeleton-placeholder text-skeleton" style={{ width: '90%', height: '12px', marginBottom: '8px' }} />
                <div className="skeleton-placeholder text-skeleton" style={{ width: '75%', height: '12px' }} />
              </div>

              <div className="lead-stats" style={{ margin: '8px 0', padding: '12px', background: 'rgba(0, 0, 0, 0.1)', borderRadius: '8px' }}>
                <div className="skeleton-placeholder text-skeleton" style={{ width: '60%', height: '12px' }} />
              </div>

              <div className="lead-footer" style={{ marginTop: 'auto' }}>
                <div className="skeleton-placeholder" style={{ flex: 1, height: '34px', borderRadius: '8px' }} />
                <div className="skeleton-placeholder" style={{ flex: 1, height: '34px', borderRadius: '8px' }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!searchResults) {
    return (
      <div className="empty-state">
        <TrendingUp size={48} />
        <p>Запустите поиск, чтобы увидеть результаты</p>
      </div>
    );
  }

  return (
    <div className="search-results-section">
      <h3>
        Результаты поиска
        <span className="result-count">({searchResults.total})</span>
      </h3>

      {searchResults.contacts.length === 0 ? (
        <div className="no-results">По вашему запросу ничего не найдено</div>
      ) : (
        <div className="leads-grid">
          {searchResults.contacts.map((contact) => (
            <LeadCard key={contact.id} contact={contact} />
          ))}
        </div>
      )}
    </div>
  );
};

export default LeadGrid;
