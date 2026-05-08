import React from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { ExternalLink, Filter } from 'lucide-react';
import './Contacts.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const Contacts: React.FC = () => {
  const [page, setPage] = React.useState(1);
  const { data, error } = useSWR(`/api/contacts?page=${page}&page_size=50`, fetcher);

  if (error) return <div className="error">Failed to load contacts</div>;
  if (!data) return <div className="loading">Loading contact database...</div>;

  const contacts = data.contacts || [];
  const total = data.total || 0;
  const totalPages = data.pages || 0;

  return (
    <div className="contacts-page">
      <div className="page-header-actions">
        <div>
          <h1 className="text-gradient">Index-Контактов</h1>
          <p className="text-secondary">Всего выявлено: {total} профилей</p>
        </div>
        <div className="actions">
          <button className="btn-venom secondary">
            <Filter size={18} />
            Фильтр
          </button>
        </div>
      </div>

      <div className="table-container serpent-card">
        <table className="modern-table">
          <thead>
            <tr>
              <th>Имя</th>
              <th>Username</th>
              <th>Источник</th>
              <th>Score</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {contacts.map((c: any) => (
              <tr key={c.id}>
                <td>
                  <div className="user-cell">
                    <div className="mini-avatar">
                      {c.first_name?.[0] || 'U'}
                    </div>
                    <span>{c.first_name} {c.last_name || ''}</span>
                  </div>
                </td>
                <td className="username-cell">@{c.telegram_username || 'Н/Д'}</td>
                <td><span className="source-tag">{c.source || 'crm'}</span></td>
                <td>
                  <div className="score-badge" style={{ backgroundColor: `rgba(16, 185, 129, ${c.lead_score / 100})` }}>
                    {c.lead_score}
                  </div>
                </td>
                <td>
                  <a href={`https://t.me/${c.telegram_username}`} target="_blank" rel="noreferrer" className="action-icon">
                    <ExternalLink size={16} />
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Pagination Controls */}
        <div className="pagination-controls">
          <button 
            disabled={page <= 1} 
            onClick={() => setPage(p => p - 1)}
            className="btn-page"
          >
            Предыдущая
          </button>
          <span className="page-info">
            Страница {page} из {totalPages}
          </span>
          <button 
            disabled={page >= totalPages} 
            onClick={() => setPage(p => p + 1)}
            className="btn-page"
          >
            Следующая
          </button>
        </div>
      </div>
    </div>
  );
};

export default Contacts;
