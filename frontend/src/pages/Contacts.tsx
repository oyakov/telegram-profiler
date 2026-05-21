import React from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { ExternalLink, Filter } from 'lucide-react';
import './Contacts.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const Contacts: React.FC = () => {
  const [page, setPage] = React.useState(1);
  const { data, error } = useSWR(`/api/contacts?page=${page}&page_size=50`, fetcher);

  const isLoading = !data && !error;

  if (error) return <div className="error">Failed to load contacts</div>;

  const contacts = data?.contacts || [];
  const total = data?.total || 0;
  const totalPages = data?.pages || 0;

  return (
    <div className="contacts-page">
      <div className="page-header-actions">
        <div>
          <h1 className="text-gradient">Index-Контактов</h1>
          {isLoading ? (
            <div className="skeleton-placeholder text-skeleton" style={{ width: '180px', marginTop: '6px' }} />
          ) : (
            <p className="text-secondary">Всего выявлено: {total} профилей</p>
          )}
        </div>
        <div className="actions">
          <button className="btn-venom secondary" disabled={isLoading}>
            <Filter size={18} />
            Фильтр
          </button>
        </div>
      </div>

      <div className="table-container serpent-card">
        {isLoading && <div className="card-loading-bar" />}
        <table className="modern-table">
          <thead>
            <tr>
              <th>Имя</th>
              <th>Username</th>
              <th>Источник</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: 10 }).map((_, idx) => (
                <tr key={`contact-row-skeleton-${idx}`}>
                  <td>
                    <div className="user-cell">
                      <div className="mini-avatar skeleton-placeholder" style={{ background: 'transparent' }} />
                      <div className="skeleton-placeholder text-skeleton" style={{ width: '120px' }} />
                    </div>
                  </td>
                  <td>
                    <div className="skeleton-placeholder text-skeleton" style={{ width: '80px' }} />
                  </td>
                  <td>
                    <div className="skeleton-placeholder text-skeleton" style={{ width: '50px' }} />
                  </td>
                  <td>
                    <div className="skeleton-placeholder text-skeleton" style={{ width: '20px' }} />
                  </td>
                </tr>
              ))
            ) : contacts.map((c: any) => (
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
            disabled={page <= 1 || isLoading} 
            onClick={() => setPage(p => p - 1)}
            className="btn-page"
          >
            Предыдущая
          </button>
          <span className="page-info">
            {isLoading ? (
              <div className="skeleton-placeholder text-skeleton" style={{ width: '100px' }} />
            ) : (
              `Страница ${page} из ${totalPages}`
            )}
          </span>
          <button 
            disabled={page >= totalPages || isLoading} 
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
