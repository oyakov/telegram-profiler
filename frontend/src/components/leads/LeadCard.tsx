import React from 'react';
import { DollarSign, MessageSquare, ExternalLink } from 'lucide-react';

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

interface Props {
  contact: Contact;
}

const LeadCard: React.FC<Props> = ({ contact }) => {
  return (
    <div className="lead-card serpent-card">
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
        <a 
          href={`https://t.me/${contact.telegram_username}`} 
          target="_blank" 
          rel="noreferrer" 
          className="btn-small primary"
        >
          <ExternalLink size={14} />
          Связаться
        </a>
      </div>
    </div>
  );
};

export default LeadCard;
