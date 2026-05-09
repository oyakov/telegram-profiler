import React, { useState } from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { ExternalLink, ChevronDown, ChevronUp, Download, Loader } from 'lucide-react';
import './PersonalContacts.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

const PersonalContacts: React.FC = () => {
  const [page, setPage] = React.useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isSyncingContacts, setIsSyncingContacts] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');

  const queryParams = new URLSearchParams();
  queryParams.append('page', page.toString());
  queryParams.append('page_size', '50');
  queryParams.append('is_personal', 'true');
  if (searchQuery) {
    queryParams.append('search', searchQuery);
  }

  const { data, error } = useSWR(
    `/api/contacts?${queryParams.toString()}`,
    fetcher
  );

  if (error) return <div className="error">Failed to load contacts</div>;
  if (!data) return <div className="loading">Loading contacts...</div>;

  const contacts = data.contacts || [];
  const total = data.total || 0;
  const totalPages = data.pages || 0;

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setPage(1);
  };

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const toggleSelect = (id: string) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === contacts.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(contacts.map((c: any) => c.id)));
    }
  };

  const handleSyncContacts = async () => {
    setIsSyncingContacts(true);
    setStatusMessage('Синхронизация контактов из Telegram...');

    try {
      const response = await api.post('/api/telegram/contacts/sync');
      setStatusMessage(`✓ Синхронизировано: +${response.data.added} контактов, обновлено: ${response.data.updated}`);
      // Refresh the contacts list
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    } catch (err) {
      setStatusMessage('Ошибка при синхронизации контактов');
      console.error(err);
    } finally {
      setIsSyncingContacts(false);
    }
  };

  const handleAddToTracked = async () => {
    if (selectedIds.size === 0) {
      setStatusMessage('Выберите хотя бы один контакт');
      return;
    }

    setIsLoadingHistory(true);
    setStatusMessage('Добавление в отслеживаемый...');

    try {
      const contactIds = Array.from(selectedIds);
      await api.post(`/api/contacts/add-to-tracked`, {
        contact_ids: contactIds,
      });
      setStatusMessage(`✓ Добавлено ${selectedIds.size} контактов в отслеживаемый`);
      setSelectedIds(new Set());
    } catch (err) {
      setStatusMessage('Ошибка при добавлении в отслеживаемый');
      console.error(err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  return (
    <div className="personal-contacts-page">
      <div className="page-header">
        <div>
          <h1 className="text-gradient">Мои Контакты</h1>
          <p className="text-secondary">Всего: {total} контактов</p>
        </div>
        <div className="header-buttons">
          <button
            onClick={handleSyncContacts}
            disabled={isSyncingContacts}
            className="btn-sync"
          >
            {isSyncingContacts ? (
              <>
                <Loader size={16} className="spinner" />
                Синхронизация...
              </>
            ) : (
              <>
                <Download size={16} />
                Синхронизировать
              </>
            )}
          </button>
          {selectedIds.size > 0 && (
            <button
              onClick={handleAddToTracked}
              disabled={isLoadingHistory}
              className="btn-fetch-history"
            >
              {isLoadingHistory ? (
                <>
                  <Loader size={16} className="spinner" />
                  Добавление...
                </>
              ) : (
                <>
                  <Download size={16} />
                  Добавить в отслеживаемый ({selectedIds.size})
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {statusMessage && (
        <div className={`status-message ${statusMessage.includes('✓') ? 'success' : 'error'}`}>
          {statusMessage}
        </div>
      )}

      <div className="search-section">
        <input
          type="text"
          placeholder="Поиск по имени, email, компании..."
          className="search-input"
          value={searchQuery}
          onChange={handleSearch}
        />
      </div>

      {contacts.length > 0 && (
        <div className="selection-bar">
          <label className="select-all-checkbox">
            <input
              type="checkbox"
              checked={selectedIds.size === contacts.length && contacts.length > 0}
              onChange={toggleSelectAll}
            />
            <span>Выбрать всё ({contacts.length})</span>
          </label>
          {selectedIds.size > 0 && (
            <span className="selected-count">Выбрано: {selectedIds.size}</span>
          )}
        </div>
      )}

      <div className="contacts-list serpent-card">
        {contacts.length === 0 ? (
          <div className="empty-state">
            <p>Нет контактов</p>
          </div>
        ) : (
          contacts.map((contact: any) => (
            <div
              key={contact.id}
              className={`contact-item ${selectedIds.has(contact.id) ? 'selected' : ''}`}
            >
              <div className="contact-header">
                <input
                  type="checkbox"
                  className="contact-checkbox"
                  checked={selectedIds.has(contact.id)}
                  onChange={() => toggleSelect(contact.id)}
                  onClick={(e) => e.stopPropagation()}
                />
                <div
                  className="contact-main-info"
                  onClick={() => toggleExpand(contact.id)}
                  style={{ flex: 1, cursor: 'pointer' }}
                >
                  <div className="mini-avatar">
                    {contact.first_name?.[0] || 'U'}
                  </div>
                  <div className="contact-summary">
                    <span className="contact-name">
                      {contact.first_name} {contact.last_name || ''}
                    </span>
                    {contact.company && (
                      <span className="contact-company">{contact.company}</span>
                    )}
                  </div>
                </div>

                <div className="contact-badges">
                  {contact.telegram_username && (
                    <span className="badge">@{contact.telegram_username}</span>
                  )}
                  {contact.email && (
                    <span className="badge">{contact.email}</span>
                  )}
                  {contact.lead_score > 0 && (
                    <div
                      className="score-badge"
                      style={{
                        backgroundColor: `rgba(16, 185, 129, ${contact.lead_score / 100})`,
                      }}
                    >
                      {Math.round(contact.lead_score)}
                    </div>
                  )}
                </div>

                <div className="expand-icon">
                  {expandedId === contact.id ? (
                    <ChevronUp size={20} />
                  ) : (
                    <ChevronDown size={20} />
                  )}
                </div>
              </div>

              {expandedId === contact.id && (
                <div className="contact-details">
                  <div className="details-grid">
                    {contact.bio && (
                      <div className="detail-item">
                        <label>Bio</label>
                        <p>{contact.bio}</p>
                      </div>
                    )}

                    {contact.position && (
                      <div className="detail-item">
                        <label>Position</label>
                        <p>{contact.position}</p>
                      </div>
                    )}

                    {contact.phone && (
                      <div className="detail-item">
                        <label>Phone</label>
                        <p>{contact.phone}</p>
                      </div>
                    )}

                    {contact.linkedin_url && (
                      <div className="detail-item">
                        <label>LinkedIn</label>
                        <a href={contact.linkedin_url} target="_blank" rel="noreferrer">
                          {contact.linkedin_url}
                        </a>
                      </div>
                    )}

                    {contact.interests && contact.interests.length > 0 && (
                      <div className="detail-item">
                        <label>Interests</label>
                        <div className="tags">
                          {contact.interests.map((interest: string, idx: number) => (
                            <span key={idx} className="tag">
                              {interest}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {contact.skills && contact.skills.length > 0 && (
                      <div className="detail-item">
                        <label>Skills</label>
                        <div className="tags">
                          {contact.skills.map((skill: string, idx: number) => (
                            <span key={idx} className="tag">
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {contact.notes && (
                      <div className="detail-item full-width">
                        <label>Notes</label>
                        <p>{contact.notes}</p>
                      </div>
                    )}

                    {contact.telegram_username && (
                      <div className="detail-item">
                        <label>Telegram</label>
                        <a href={`https://t.me/${contact.telegram_username}`} target="_blank" rel="noreferrer" className="telegram-link">
                          <ExternalLink size={16} />
                          t.me/{contact.telegram_username}
                        </a>
                      </div>
                    )}
                  </div>

                  <div className="details-footer">
                    {contact.created_at && (
                      <span className="meta-info">
                        Added: {new Date(contact.created_at).toLocaleDateString()}
                      </span>
                    )}
                    {contact.last_interaction && (
                      <span className="meta-info">
                        Last interaction: {new Date(contact.last_interaction).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {totalPages > 1 && (
        <div className="pagination-controls">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="btn-page"
          >
            Предыдущая
          </button>
          <span className="page-info">
            Страница {page} из {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="btn-page"
          >
            Следующая
          </button>
        </div>
      )}
    </div>
  );
};

export default PersonalContacts;
