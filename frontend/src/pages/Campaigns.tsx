import React, { useState, useMemo } from 'react';
import useSWR from 'swr';
import api from '../services/api';
import {
  Send,
  X,
  Plus,
  Loader,
  Trash2,
  Eye,
  FileUp,
  Users,
  CheckSquare,
  Upload,
} from 'lucide-react';
import './Campaigns.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

interface Campaign {
  id: string;
  name: string;
  status: string;
  total_contacts: number;
  sent_count: number;
  failed_count: number;
  created_at: string;
  updated_at: string;
}

interface Contact {
  id: string;
  first_name: string;
  last_name: string;
  email?: string;
  telegram_username?: string;
  company?: string;
  lead_score: number;
}

const Campaigns: React.FC = () => {
  const [campaignName, setCampaignName] = useState('');
  const [campaignDescription, setCampaignDescription] = useState('');
  const [campaignMessage, setCampaignMessage] = useState('');
  const [selectedTab, setSelectedTab] = useState<'file' | 'database' | 'selected'>('database');
  const [selectedContacts, setSelectedContacts] = useState<Set<string>>(new Set());
  const [isCreating, setIsCreating] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [loadedContacts, setLoadedContacts] = useState<Contact[]>([]);
  const [fileContacts, setFileContacts] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [databasePage, setDatabasePage] = useState(1);

  // Fetch campaigns
  const { data: campaignsData, mutate: mutateCampaigns } = useSWR(
    `/api/campaigns?status=${statusFilter}&page=${1}&page_size=50`,
    fetcher
  );

  // Fetch contacts from database
  const { data: contactsData } = useSWR(
    `/api/contacts?page=${databasePage}&page_size=100`,
    fetcher
  );

  const campaigns = campaignsData?.campaigns || [];

  // Filter database contacts by search
  const databaseContacts = useMemo(() => {
    if (!contactsData?.contacts) return [];
    if (!searchQuery) return contactsData.contacts;
    const q = searchQuery.toLowerCase();
    return contactsData.contacts.filter((c: Contact) =>
      `${c.first_name} ${c.last_name} ${c.email || ''} ${c.company || ''}`.toLowerCase().includes(q)
    );
  }, [contactsData, searchQuery]);

  // Handle file upload
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const csv = event.target?.result as string;
      const lines = csv.split('\n').filter(line => line.trim());
      const headers = lines[0].split(',').map(h => h.trim().toLowerCase());

      const contacts = lines.slice(1).map(line => {
        const values = line.split(',').map(v => v.trim());
        const obj: any = {};
        headers.forEach((header, idx) => {
          obj[header] = values[idx];
        });
        return obj;
      });

      setFileContacts(contacts);
      setSelectedTab('file');
    };
    reader.readAsText(file);
  };

  // Toggle contact selection
  const toggleContactSelection = (contactId: string) => {
    const newSelected = new Set(selectedContacts);
    if (newSelected.has(contactId)) {
      newSelected.delete(contactId);
    } else {
      newSelected.add(contactId);
    }
    setSelectedContacts(newSelected);
  };

  // Select all/none from database
  const toggleSelectAll = () => {
    if (selectedContacts.size === databaseContacts.length) {
      setSelectedContacts(new Set());
    } else {
      setSelectedContacts(new Set(databaseContacts.map(c => c.id)));
    }
  };

  // Add file contacts to selection
  const addFileContacts = () => {
    const newSelected = new Set(selectedContacts);
    fileContacts.forEach((_, idx) => {
      newSelected.add(`file-${idx}`);
    });
    setSelectedContacts(newSelected);
    setFileContacts([]);
    setSelectedTab('selected');
  };

  // Create campaign
  const handleCreateCampaign = async () => {
    if (!campaignName.trim() || !campaignMessage.trim() || selectedContacts.size === 0) {
      alert('Заполните все поля и выберите контакты');
      return;
    }

    setIsCreating(true);
    try {
      // Separate file and database contacts
      const dbContactIds = Array.from(selectedContacts)
        .filter(id => !id.startsWith('file-'))
        .map(id => id);

      // If there are file contacts, we'd normally import them first
      // For now, just use selected database contacts
      if (dbContactIds.length === 0) {
        alert('Выберите контакты для рассылки');
        setIsCreating(false);
        return;
      }

      const res = await api.post('/api/campaigns', {
        name: campaignName,
        description: campaignDescription,
        message: campaignMessage,
        contact_ids: dbContactIds,
      });

      if (res.data.id) {
        // Clear form
        setCampaignName('');
        setCampaignDescription('');
        setCampaignMessage('');
        setSelectedContacts(new Set());
        setFileContacts([]);

        // Refresh campaigns list
        mutateCampaigns();
        alert('Кампания создана!');
      }
    } catch (err: any) {
      alert(`Ошибка: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsCreating(false);
    }
  };

  // Send campaign
  const handleSendCampaign = async (campaignId: string) => {
    if (!window.confirm('Отправить кампанию? Это действие нельзя отменить.')) {
      return;
    }

    setIsSending(true);
    try {
      await api.post(`/api/campaigns/${campaignId}/send`);
      mutateCampaigns();
      alert('Кампания отправляется...');
    } catch (err: any) {
      alert(`Ошибка: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsSending(false);
    }
  };

  // Delete campaign
  const handleDeleteCampaign = async (campaignId: string) => {
    if (!window.confirm('Удалить кампанию?')) {
      return;
    }

    try {
      await api.delete(`/api/campaigns/${campaignId}`);
      mutateCampaigns();
    } catch (err: any) {
      alert(`Ошибка: ${err.response?.data?.detail || err.message}`);
    }
  };

  // Get selected contacts count
  const totalSelected = selectedContacts.size;
  const databaseSelected = Array.from(selectedContacts).filter(id => !id.startsWith('file-')).length;
  const fileSelected = Array.from(selectedContacts).filter(id => id.startsWith('file-')).length;

  return (
    <div className="campaigns-page">
      <div className="page-header-actions">
        <div>
          <h1 className="text-gradient">Кампании</h1>
          <p className="text-secondary">Создание и управление массовыми рассылками сообщений</p>
        </div>
      </div>

      <div className="campaigns-container">
        {/* Left: Campaign Form */}
        <div className="campaign-form-panel">
          <h2>Создать кампанию</h2>

          <div className="form-section">
            <label>Название кампании</label>
            <input
              type="text"
              placeholder="Например: Приглашение на вебинар"
              value={campaignName}
              onChange={(e) => setCampaignName(e.target.value)}
              className="form-input"
            />
          </div>

          <div className="form-section">
            <label>Описание (опционально)</label>
            <textarea
              placeholder="Описание для справки..."
              value={campaignDescription}
              onChange={(e) => setCampaignDescription(e.target.value)}
              className="form-textarea"
              rows={2}
            />
          </div>

          <div className="form-section">
            <label>Текст сообщения</label>
            <p className="form-hint">Используйте {'{first_name}'}, {'{last_name}'}, {'{email}'}, {'{company}'} для подстановки</p>
            <textarea
              placeholder="Привет {first_name}! Вот сообщение для вас..."
              value={campaignMessage}
              onChange={(e) => setCampaignMessage(e.target.value)}
              className="form-textarea"
              rows={5}
            />
          </div>

          <div className="form-section">
            <label>Предпросмотр</label>
            <div className="preview-box">
              {campaignMessage
                ? campaignMessage
                    .replace(/{first_name}/g, 'Иван')
                    .replace(/{last_name}/g, 'Петров')
                    .replace(/{email}/g, 'ivan@example.com')
                    .replace(/{company}/g, 'Компания')
                : 'Текст сообщения появится здесь'}
            </div>
          </div>

          <div className="form-section">
            <label>Выбрано контактов</label>
            <div className="contacts-stats">
              <div className="stat">
                <span className="label">Всего:</span>
                <span className="value">{totalSelected}</span>
              </div>
              {databaseSelected > 0 && (
                <div className="stat">
                  <span className="label">Из базы:</span>
                  <span className="value">{databaseSelected}</span>
                </div>
              )}
              {fileSelected > 0 && (
                <div className="stat">
                  <span className="label">Из файла:</span>
                  <span className="value">{fileSelected}</span>
                </div>
              )}
            </div>
          </div>

          <div className="form-actions">
            <button
              className="btn-venom primary"
              onClick={handleCreateCampaign}
              disabled={isCreating || totalSelected === 0}
            >
              {isCreating ? (
                <>
                  <Loader size={18} className="spinner" />
                  Создание...
                </>
              ) : (
                <>
                  <Plus size={18} />
                  Создать кампанию
                </>
              )}
            </button>
          </div>
        </div>

        {/* Middle: Contact Selector */}
        <div className="contact-selector-panel">
          <h2>Выбор контактов</h2>

          <div className="selector-tabs">
            <button
              className={`tab ${selectedTab === 'file' ? 'active' : ''}`}
              onClick={() => setSelectedTab('file')}
            >
              <FileUp size={16} />
              Из файла
            </button>
            <button
              className={`tab ${selectedTab === 'database' ? 'active' : ''}`}
              onClick={() => setSelectedTab('database')}
            >
              <Users size={16} />
              Из базы
            </button>
            <button
              className={`tab ${selectedTab === 'selected' ? 'active' : ''}`}
              onClick={() => setSelectedTab('selected')}
            >
              <CheckSquare size={16} />
              Выбранные ({totalSelected})
            </button>
          </div>

          {/* File Upload Tab */}
          {selectedTab === 'file' && (
            <div className="tab-content">
              <div className="file-upload-area">
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileUpload}
                  className="file-input"
                />
                <div className="upload-hint">
                  <Upload size={32} />
                  <p>Загрузите CSV или XLSX файл с контактами</p>
                </div>
              </div>

              {fileContacts.length > 0 && (
                <>
                  <div className="file-preview">
                    <h3>Предпросмотр (первые 5)</h3>
                    <div className="contacts-list">
                      {fileContacts.slice(0, 5).map((contact, idx) => (
                        <div key={idx} className="contact-item">
                          <span>{contact.first_name || contact.name || 'Контакт'} {contact.last_name || ''}</span>
                          {contact.email && <span className="email">{contact.email}</span>}
                        </div>
                      ))}
                    </div>
                    <p className="text-secondary">Всего в файле: {fileContacts.length} контактов</p>
                  </div>

                  <button className="btn-venom primary" onClick={addFileContacts}>
                    <Plus size={16} />
                    Добавить все ({fileContacts.length})
                  </button>
                </>
              )}
            </div>
          )}

          {/* Database Contacts Tab */}
          {selectedTab === 'database' && (
            <div className="tab-content">
              <div className="search-box">
                <input
                  type="text"
                  placeholder="Поиск по имени, email, компании..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="form-input"
                />
              </div>

              {databaseContacts.length > 0 && (
                <>
                  <div className="select-all-box">
                    <label>
                      <input
                        type="checkbox"
                        checked={selectedContacts.size > 0 && selectedContacts.size === databaseContacts.length}
                        onChange={toggleSelectAll}
                      />
                      Выбрать все ({databaseContacts.length})
                    </label>
                  </div>

                  <div className="contacts-list">
                    {databaseContacts.map((contact) => (
                      <div key={contact.id} className="contact-item">
                        <input
                          type="checkbox"
                          checked={selectedContacts.has(contact.id)}
                          onChange={() => toggleContactSelection(contact.id)}
                        />
                        <div className="contact-info">
                          <span className="name">{contact.first_name} {contact.last_name}</span>
                          {contact.email && <span className="email">{contact.email}</span>}
                          {contact.company && <span className="company">{contact.company}</span>}
                        </div>
                        <span className="score">{contact.lead_score}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {databaseContacts.length === 0 && (
                <div className="empty-state">
                  <Users size={32} />
                  <p>Контакты не найдены</p>
                </div>
              )}
            </div>
          )}

          {/* Selected Contacts Tab */}
          {selectedTab === 'selected' && (
            <div className="tab-content">
              {totalSelected > 0 ? (
                <>
                  <div className="contacts-list">
                    {Array.from(selectedContacts).map((contactId) => {
                      if (contactId.startsWith('file-')) {
                        const idx = parseInt(contactId.replace('file-', ''));
                        const contact = fileContacts[idx];
                        return (
                          <div key={contactId} className="contact-item">
                            <div className="contact-info">
                              <span className="name">{contact.first_name || contact.name}</span>
                              {contact.email && <span className="email">{contact.email}</span>}
                            </div>
                            <button
                              onClick={() => toggleContactSelection(contactId)}
                              className="remove-btn"
                            >
                              <X size={16} />
                            </button>
                          </div>
                        );
                      }

                      const contact = databaseContacts.find(c => c.id === contactId);
                      if (!contact) return null;

                      return (
                        <div key={contactId} className="contact-item">
                          <div className="contact-info">
                            <span className="name">{contact.first_name} {contact.last_name}</span>
                            {contact.email && <span className="email">{contact.email}</span>}
                          </div>
                          <button
                            onClick={() => toggleContactSelection(contactId)}
                            className="remove-btn"
                          >
                            <X size={16} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                  <button
                    className="btn-small danger"
                    onClick={() => setSelectedContacts(new Set())}
                  >
                    Очистить все
                  </button>
                </>
              ) : (
                <div className="empty-state">
                  <CheckSquare size={32} />
                  <p>Никакие контакты не выбраны</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right: Campaigns List */}
        <div className="campaigns-list-panel">
          <h2>Кампании</h2>

          <div className="filter-box">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="form-input"
            >
              <option value="">Все статусы</option>
              <option value="draft">Черновик</option>
              <option value="sending">Отправляется</option>
              <option value="completed">Завершена</option>
              <option value="failed">Ошибка</option>
            </select>
          </div>

          {campaigns.length > 0 ? (
            <div className="campaigns-grid">
              {campaigns.map((campaign: Campaign) => (
                <div key={campaign.id} className="campaign-card serpent-card">
                  <div className="campaign-header">
                    <h4>{campaign.name}</h4>
                    <span className={`status status-${campaign.status}`}>
                      {campaign.status === 'draft' && 'Черновик'}
                      {campaign.status === 'sending' && 'Отправляется'}
                      {campaign.status === 'completed' && 'Завершена'}
                      {campaign.status === 'failed' && 'Ошибка'}
                    </span>
                  </div>

                  <div className="campaign-stats">
                    <div className="stat">
                      <span className="label">Контактов:</span>
                      <span className="value">{campaign.total_contacts}</span>
                    </div>
                    <div className="stat">
                      <span className="label">Отправлено:</span>
                      <span className="value success">{campaign.sent_count}</span>
                    </div>
                    {campaign.failed_count > 0 && (
                      <div className="stat">
                        <span className="label">Ошибок:</span>
                        <span className="value error">{campaign.failed_count}</span>
                      </div>
                    )}
                  </div>

                  <div className="campaign-progress">
                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{
                          width: `${campaign.total_contacts > 0
                            ? ((campaign.sent_count + campaign.failed_count) / campaign.total_contacts) * 100
                            : 0
                          }%`,
                        }}
                      />
                    </div>
                  </div>

                  <div className="campaign-date">
                    {new Date(campaign.created_at).toLocaleDateString('ru-RU')}
                  </div>

                  <div className="campaign-actions">
                    {campaign.status === 'draft' && (
                      <>
                        <button
                          className="btn-small primary"
                          onClick={() => handleSendCampaign(campaign.id)}
                          disabled={isSending}
                        >
                          <Send size={14} />
                          Отправить
                        </button>
                        <button
                          className="btn-small danger"
                          onClick={() => handleDeleteCampaign(campaign.id)}
                        >
                          <Trash2 size={14} />
                        </button>
                      </>
                    )}
                    {campaign.status !== 'draft' && (
                      <button className="btn-small secondary">
                        <Eye size={14} />
                        Детали
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <Send size={48} />
              <p>Кампаний нет. Создайте новую!</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Campaigns;
