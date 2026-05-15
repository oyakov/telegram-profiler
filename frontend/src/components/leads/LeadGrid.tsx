import React from 'react';
import { TrendingUp } from 'lucide-react';
import LeadCard from './LeadCard';
import { LeadSearchResult } from '../../hooks/useLeads';

interface Props {
  searchResults: LeadSearchResult | null;
}

const LeadGrid: React.FC<Props> = ({ searchResults }) => {
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
