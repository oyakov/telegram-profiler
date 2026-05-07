import React from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { ExternalLink, Filter } from 'lucide-react';
import './Contacts.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const Contacts: React.FC = () => {
  const { data, error } = useSWR('/api/contacts', fetcher);

  if (error) return <div className="error">Failed to load contacts</div>;
  if (!data) return <div className="loading">Loading contact database...</div>;

  const contacts = data.contacts || [];

  return (
    <div className="contacts-page">
      <div className="page-header-actions">
        <div>
          <h1 className="text-gradient">База Контактов</h1>
          <p className="text-secondary">Всего выявлено: {contacts.length} профилей</p>
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
      </div>
    </div>
  );
};

export default Contacts;
