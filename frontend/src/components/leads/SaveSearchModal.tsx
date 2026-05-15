import React from 'react';
import { X } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  searchName: string;
  setSearchName: (name: string) => void;
  searchDescription: string;
  setSearchDescription: (desc: string) => void;
  onSave: () => void;
  savingSearch: boolean;
}

const SaveSearchModal: React.FC<Props> = ({
  isOpen,
  onClose,
  searchName,
  setSearchName,
  searchDescription,
  setSearchDescription,
  onSave,
  savingSearch,
}) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Сохранить поиск</h3>
          <button className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          <div className="form-group">
            <label>Название</label>
            <input
              type="text"
              placeholder="Мой поиск лидов..."
              value={searchName}
              onChange={(e) => setSearchName(e.target.value)}
              className="form-input"
              autoFocus
            />
          </div>

          <div className="form-group">
            <label>Описание (опционально)</label>
            <textarea
              placeholder="Описание этого поиска..."
              value={searchDescription}
              onChange={(e) => setSearchDescription(e.target.value)}
              className="form-textarea"
              rows={3}
            />
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn secondary" onClick={onClose}>
            Отмена
          </button>
          <button
            className="btn primary"
            onClick={onSave}
            disabled={savingSearch || !searchName.trim()}
          >
            {savingSearch ? 'Сохранение...' : 'Сохранить'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SaveSearchModal;
