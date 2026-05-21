import React, { useState } from 'react';
import useSWR from 'swr';
import api from '../services/api';
import { Plus, Trash2, Edit2, Database, ExternalLink, Info } from 'lucide-react';
import './Projects.css';

const fetcher = (url: string) => api.get(url).then(res => res.data);

interface Project {
  id: string;
  name: string;
  db_name: string;
  description?: string;
  is_active: boolean;
}

const Projects: React.FC = () => {
  const { data: projects, error: projectsError, mutate } = useSWR('/api/projects', fetcher);
  const isLoading = !projects && !projectsError;
  const [showModal, setShowModal] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [formData, setFormData] = useState({ name: '', description: '' });

  const handleCreateOrUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingProject) {
        await api.patch(`/api/projects/${editingProject.id}`, formData);
      } else {
        await api.post('/api/projects', formData);
      }
      setShowModal(false);
      setEditingProject(null);
      setFormData({ name: '', description: '' });
      mutate();
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || 'Operation failed'));
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Remove project "${name}"? The database will NOT be deleted, but the record will be removed from the list.`)) return;
    try {
      await api.delete(`/api/projects/${id}`);
      mutate();
    } catch (err: any) {
      alert('Error: ' + (err.response?.data?.detail || 'Delete failed'));
    }
  };

  return (
    <div className="projects-page">
      <div className="page-header-actions">
        <div>
          <h1 className="text-gradient">Управление Проектами</h1>
          <p className="text-secondary">Изолированные рабочие пространства и базы данных</p>
        </div>
        <button 
          className="btn-venom primary" 
          onClick={() => { setEditingProject(null); setFormData({ name: '', description: '' }); setShowModal(true); }}
          disabled={isLoading}
        >
          <Plus size={18} />
          Новый проект
        </button>
      </div>

      <div className="projects-grid">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, idx) => (
            <div key={`project-skeleton-${idx}`} className="project-card serpent-card no-hover" style={{ position: 'relative', overflow: 'hidden' }}>
              <div className="card-loading-bar" />
              <div className="project-card-header" style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div className="project-icon skeleton-placeholder" style={{ background: 'transparent' }} />
                <div className="project-actions" style={{ display: 'flex', gap: '0.5rem' }}>
                  <div className="skeleton-placeholder" style={{ width: '32px', height: '32px', borderRadius: '8px' }} />
                  <div className="skeleton-placeholder" style={{ width: '32px', height: '32px', borderRadius: '8px' }} />
                </div>
              </div>
              <div className="project-card-body" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div className="skeleton-placeholder text-skeleton" style={{ width: '160px', height: '1.5rem' }} />
                <div className="skeleton-placeholder text-skeleton" style={{ width: '100px', height: '0.9rem' }} />
                <div className="skeleton-placeholder text-skeleton" style={{ width: '220px', height: '1rem', marginTop: '12px' }} />
              </div>
              <div className="project-card-footer" style={{ marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid rgba(255, 255, 255, 0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div className="skeleton-placeholder" style={{ width: '70px', height: '18px', borderRadius: '4px' }} />
                <div className="skeleton-placeholder" style={{ width: '90px', height: '32px', borderRadius: '8px' }} />
              </div>
            </div>
          ))
        ) : (projects || []).map((project: Project) => (
          <div key={project.id} className="project-card serpent-card">
            <div className="project-card-header">
              <div className="project-icon">
                <Database size={24} className="text-accent" />
              </div>
              <div className="project-actions">
                <button onClick={() => { setEditingProject(project); setFormData({ name: project.name, description: project.description || '' }); setShowModal(true); }} className="action-btn">
                  <Edit2 size={14} />
                </button>
                <button onClick={() => handleDelete(project.id, project.name)} className="action-btn delete">
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
            
            <div className="project-card-body">
              <h3>{project.name}</h3>
              <p className="db-name"><code>{project.db_name}</code></p>
              <p className="description">{project.description || 'Нет описания'}</p>
            </div>

            <div className="project-card-footer">
               <div className="status-badge">
                 <div className={`pulse-dot ${project.is_active ? 'active' : ''}`}></div>
                 <span>{project.is_active ? 'Активен' : 'Архив'}</span>
               </div>
               <button className="btn-open" onClick={() => { localStorage.setItem('selected_db', project.db_name); window.location.href = '/'; }}>
                 Открыть <ExternalLink size={14} />
               </button>
            </div>
          </div>
        ))}
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content serpent-card">
            <h2>{editingProject ? 'Редактировать проект' : 'Создать новый проект'}</h2>
            <form onSubmit={handleCreateOrUpdate}>
              <div className="form-group">
                <label>Название проекта</label>
                <input 
                  type="text" 
                  value={formData.name} 
                  onChange={e => setFormData({...formData, name: e.target.value})}
                  placeholder="Напр: Крипто Аналитика"
                  required
                />
              </div>
              <div className="form-group">
                <label>Описание</label>
                <textarea 
                  value={formData.description} 
                  onChange={e => setFormData({...formData, description: e.target.value})}
                  placeholder="Краткое описание целей проекта..."
                  rows={3}
                />
              </div>
              {!editingProject && (
                <div className="form-info">
                  <Info size={14} />
                  <span>Для проекта будет создана отдельная база данных PostgreSQL.</span>
                </div>
              )}
              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={() => setShowModal(false)}>Отмена</button>
                <button type="submit" className="btn-submit">{editingProject ? 'Сохранить' : 'Создать'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Projects;
