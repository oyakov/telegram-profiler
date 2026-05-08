import React, { useState, useEffect } from 'react';
import { 
  Database, Folder, MessageSquare, ChevronRight, ChevronDown, 
  Cpu, HardDrive, Zap, Cloud, Activity, CheckCircle, AlertCircle
} from 'lucide-react';

interface TreeNode {
  id: string;
  name: string;
  type: 'project' | 'folder' | 'channel';
  files: number;
  percentage: number;
  children?: TreeNode[];
  status?: string;
  username?: string;
  last_change?: string;
}

const Pacman: React.FC<{ size?: number; active?: boolean }> = ({ size = 16, active = true }) => {
  if (!active) return <div style={{ width: size, height: size, borderRadius: '50%', background: '#475569', opacity: 0.3 }}></div>;
  return (
    <div className="pacman-container" style={{ width: size, height: size }}>
      <div className="pacman-top"></div>
      <div className="pacman-bottom"></div>
    </div>
  );
};

const TreeRow: React.FC<{ node: TreeNode; level: number }> = ({ node, level }) => {
  const [isOpen, setIsOpen] = useState(level < 1);
  const hasChildren = node.children && node.children.length > 0;

  const getIcon = () => {
    switch (node.type) {
      case 'project': return <Database size={14} className="text-blue" />;
      case 'folder': return <Folder size={14} className="text-orange" />;
      case 'channel': return <MessageSquare size={14} className="text-emerald" />;
      default: return null;
    }
  };

  return (
    <>
      <div className={`tree-row level-${level} ${node.type}`} onClick={() => hasChildren && setIsOpen(!isOpen)}>
        <div className="tree-col name-col" style={{ paddingLeft: level * 20 + 8 }}>
          <div className="chevron-wrapper">
            {hasChildren && (isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />)}
          </div>
          {getIcon()}
          <span className="node-name">{node.name}</span>
          {node.username && <span className="node-username">@{node.username}</span>}
        </div>
        
        <div className="tree-col pct-col">
          <div className="pacman-track">
            <Pacman active={node.percentage > 0} />
            <div className="progress-mini">
              <div className="progress-mini-fill" style={{ width: `${node.percentage}%` }}></div>
            </div>
            <span className="pct-text">{node.percentage}%</span>
          </div>
        </div>

        <div className="tree-col files-col">
          {node.files.toLocaleString()} msg
        </div>

        <div className="tree-col change-col">
          {node.last_change ? new Date(node.last_change).toLocaleTimeString() : '—'}
        </div>
      </div>
      
      {isOpen && hasChildren && (
        <div className="tree-children">
          {node.children!.map(child => (
            <TreeRow key={child.id} node={child} level={level + 1} />
          ))}
        </div>
      )}
    </>
  );
};

export const DataFlowTree: React.FC<{ tree: TreeNode[] }> = ({ tree }) => {
  return (
    <div className="data-flow-tree serpent-card">
      <div className="tree-header">
        <div className="tree-col name-col">Иерархия данных</div>
        <div className="tree-col pct-col">Заполнение</div>
        <div className="tree-col files-col">Сообщений</div>
        <div className="tree-col change-col">Активность</div>
      </div>
      <div className="tree-body">
        {tree.map(node => (
          <TreeRow key={node.id} node={node} level={0} />
        ))}
      </div>
    </div>
  );
};

export const SystemFlow: React.FC<{ lmStatus: boolean }> = ({ lmStatus }) => {
  return (
    <div className="system-flow-container serpent-card">
      <div className="flow-nodes">
        <div className="flow-node telegram pulse">
          <Cloud size={24} />
          <span>Telegram API</span>
          <div className="node-status online"></div>
        </div>
        
        <div className="flow-connector">
          <div className="flow-particles"></div>
        </div>

        <div className="flow-node conductor">
          <Activity size={24} />
          <span>Conductor</span>
          <div className="node-status online"></div>
        </div>

        <div className="flow-connector">
          <div className="flow-particles reverse"></div>
        </div>

        <div className="flow-node-group">
          <div className={`flow-node lmstudio ${lmStatus ? 'online' : 'offline'}`}>
            <Cpu size={24} />
            <span>LMStudio</span>
            <div className={`node-status ${lmStatus ? 'online' : 'offline'}`}></div>
          </div>
          <div className="flow-node db">
            <HardDrive size={24} />
            <span>Postgres DB</span>
            <div className="node-status online"></div>
          </div>
        </div>
      </div>
      
      <div className="flow-description">
        <div className="flow-info">
          <Zap size={14} className="text-venom" />
          <span>Поток данных: <strong>142 msg/min</strong></span>
        </div>
        <div className="flow-info">
          <Activity size={14} className="text-blue" />
          <span>Embeddings: <strong>{lmStatus ? 'Активно' : 'Ожидание'}</strong></span>
        </div>
      </div>
    </div>
  );
};
