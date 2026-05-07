import React from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { TrendingUp, DollarSign, MessageSquare, ExternalLink } from 'lucide-react';
import './Leads.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const Leads: React.FC = () => {
  const { data, error, mutate } = useSWR('/api/leads/top?min_score=10', fetcher);

  const handleReprocess = async () => {
    try {
      await api.post('/api/leads/process');
      alert('Перерасчет лидов запущен');
      mutate();
    } catch (err) {
      console.error(err);
    }
  };

  if (error) return <div className="error">Failed to load leads</div>;
  if (!data) return <div className="loading">Analyzing commercial intent...</div>;

  const leads = data.contacts || [];

  return (
    <div className="leads-page">
      <div className="page-header-actions">
        <div>
          <h1 className="text-gradient">Лиды и Рекламодатели</h1>
          <p className="text-secondary">Автоматически выявленные коммерческие запросы</p>
        </div>
        <div className="actions">
          <button className="btn-venom primary" onClick={handleReprocess}>
            <TrendingUp size={18} />
            Пересчитать всё
          </button>
        </div>
      </div>

      <div className="leads-grid">
        {leads.map((l: any) => (
          <div key={l.id} className="lead-card serpent-card">
            <div className="lead-header">
              <div className="lead-main">
                <div className="lead-avatar">
                  <DollarSign size={20} />
                </div>
                <div>
                  <h4>{l.first_name} {l.last_name || ''}</h4>
                  <span className="username">@{l.telegram_username || 'private'}</span>
                </div>
              </div>
              <div className="lead-score-box">
                <span className="label">Score</span>
                <span className="value">{l.lead_score}</span>
              </div>
            </div>

            <div className="lead-stats">
              <div className="stat-item">
                <MessageSquare size={14} />
                <span>Активность: {l.our_channel_ratio}% в канале</span>
              </div>
            </div>

            <div className="lead-footer">
              <button className="btn-small secondary">История</button>
              <a href={`https://t.me/${l.telegram_username}`} target="_blank" rel="noreferrer" className="btn-small primary">
                <ExternalLink size={14} />
                Связаться
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Leads;
