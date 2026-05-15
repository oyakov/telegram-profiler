import React from 'react';
import { X, Tag } from 'lucide-react';

interface FolderEditModalProps {
  folder: any;
  formData: { name: string, description: string, tags_str: string };
  setFormData: (data: any) => void;
  onClose: () => void;
  onSubmit: (e: React.FormEvent) => void;
}

const FolderEditModal: React.FC<FolderEditModalProps> = ({ folder, formData, setFormData, onClose, onSubmit }) => {
  return (
    <div className="modal-overlay" style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1100 }}>
      <div className="modal-content serpent-card" style={{ width: '450px', padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Настройки папки</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}><X size={20} /></button>
        </div>
        <form onSubmit={onSubmit}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>Имя папки</label>
            <input 
              type="text" 
              value={formData.name} 
              onChange={e => setFormData({...formData, name: e.target.value})}
              style={{ width: '100%', padding: '10px', background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', color: 'white' }}
              required
            />
          </div>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>Описание</label>
            <textarea 
              value={formData.description} 
              onChange={e => setFormData({...formData, description: e.target.value})}
              style={{ width: '100%', padding: '10px', background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', color: 'white', minHeight: '80px' }}
              placeholder="О чем эта папка..."
            />
          </div>
          <div style={{ marginBottom: '24px' }}>
            <label style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginBottom: '6px' }}>Тэги / Ключевые слова (через запятую)</label>
            <div style={{ position: 'relative' }}>
              <Tag size={14} style={{ position: 'absolute', left: '10px', top: '12px', color: '#64748b' }} />
              <input 
                type="text" 
                value={formData.tags_str} 
                onChange={e => setFormData({...formData, tags_str: e.target.value})}
                style={{ width: '100%', padding: '10px 10px 10px 32px', background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', color: 'white' }}
                placeholder="crypto, airdrops, news..."
              />
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button type="button" onClick={onClose} style={{ padding: '10px 16px', background: 'transparent', border: '1px solid #1e293b', color: '#94a3b8', borderRadius: '8px', cursor: 'pointer' }}>Отмена</button>
            <button type="submit" style={{ padding: '10px 20px', background: '#10b981', border: 'none', color: 'white', borderRadius: '8px', fontWeight: '600', cursor: 'pointer' }}>Сохранить</button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default FolderEditModal;
