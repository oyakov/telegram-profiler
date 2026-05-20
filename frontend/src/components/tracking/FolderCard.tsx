import React from 'react';
import {
  ChevronDown, ChevronRight, Folder, FolderOpen,
  Settings as SettingsIcon, Download, Trash2,
} from 'lucide-react';
import ChannelRow from './ChannelRow';
import './FolderCard.css';

interface TgFolder {
  id: string | number;
  name: string;
  channel_count: number;
  peer_ids: any[];
}

interface FolderCardProps {
  folder: any;
  channels: any[];
  isCollapsed: boolean;
  onToggle: (id: string) => void;
  onEdit: (folder: any) => void;
  onImport: (id: string) => void;
  onDelete: (id: string, name: string) => void;
  onDeleteChannel: (id: string, title: string) => void;
  importingFolderId: string | null;
  tgFolders: TgFolder[];
  tgFoldersLoading: boolean;
  onCloseImport: () => void;
  onImportFromTg: (folderId: string, tgFolder: TgFolder) => void;
}

const FolderCard: React.FC<FolderCardProps> = ({
  folder, channels, isCollapsed, onToggle, onEdit, onImport, onDelete,
  onDeleteChannel, importingFolderId, tgFolders, tgFoldersLoading,
  onCloseImport, onImportFromTg,
}) => {
  return (
    <div className="folder-card">
      {/* Заголовок папки */}
      <div
        className={`folder-header ${isCollapsed ? '' : 'expanded'}`}
        onClick={() => onToggle(folder.id)}
      >
        <div className="folder-header-left">
          {isCollapsed
            ? <ChevronRight size={16} className="folder-chevron" />
            : <ChevronDown size={16} className="folder-chevron" />}
          {isCollapsed
            ? <Folder size={16} className="folder-icon" />
            : <FolderOpen size={16} className="folder-icon" />}
          <div className="folder-name-block">
            <span className="folder-name">{folder.name}</span>
            {folder.tags?.length > 0 && (
              <div className="folder-tags">
                {folder.tags.map((tag: string) => (
                  <span key={tag} className="folder-tag">#{tag}</span>
                ))}
              </div>
            )}
          </div>
          <span className="folder-count">{channels.length}</span>
        </div>
        <div className="folder-actions">
          <button
            className="folder-btn"
            onClick={e => { e.stopPropagation(); onEdit(folder); }}
            title="Настройки папки"
            aria-label="Редактировать папку"
          >
            <SettingsIcon size={13} />
          </button>
          <button
            className="folder-btn folder-btn--import"
            onClick={e => { e.stopPropagation(); onImport(folder.id); }}
            title="Импортировать каналы из Telegram"
          >
            <Download size={12} /> Импорт
          </button>
          <button
            className="folder-btn folder-btn--danger"
            onClick={e => { e.stopPropagation(); onDelete(folder.id, folder.name); }}
            title="Удалить папку"
            aria-label="Удалить папку"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      {/* Импорт из Telegram */}
      {importingFolderId === folder.id && (
        <div className="folder-import-panel">
          <div className="folder-import-header">
            <span>Выберите папку Telegram для импорта:</span>
            <button className="folder-import-close" onClick={onCloseImport} aria-label="Закрыть">×</button>
          </div>
          {tgFoldersLoading ? (
            <div className="folder-import-status">Загрузка папок Telegram...</div>
          ) : tgFolders.length === 0 ? (
            <div className="folder-import-status">Папки Telegram не найдены (или нет авторизации)</div>
          ) : (
            <div className="folder-import-list">
              {tgFolders.map(tf => (
                <button
                  key={tf.id}
                  className="folder-import-item"
                  onClick={() => onImportFromTg(folder.id, tf)}
                >
                  <Folder size={13} />
                  {tf.name}
                  <span className="folder-import-count">{tf.channel_count}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Таблица каналов */}
      {!isCollapsed && (
        <table className="channels-table">
          {channels.length > 0 && (
            <thead>
              <tr>
                <th>Канал</th>
                <th>Тип</th>
                <th className="text-right">Сообщений</th>
                <th>Последняя синхронизация</th>
                <th className="text-center">Действия</th>
              </tr>
            </thead>
          )}
          <tbody>
            {channels.map(ch => (
              <ChannelRow key={ch.id} ch={ch} onDelete={onDeleteChannel} />
            ))}
            {channels.length === 0 && (
              <tr>
                <td colSpan={5} className="channels-empty">
                  Нет каналов в этой папке
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default FolderCard;
