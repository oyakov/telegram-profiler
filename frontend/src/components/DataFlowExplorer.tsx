import React, { useState } from 'react';
import {
  Database, Folder, MessageSquare, ChevronRight, ChevronDown,
  Cpu, HardDrive, Zap, Cloud, Activity, Play
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

const TreeRow: React.FC<{ node: TreeNode; level: number; onSync?: (folderId: string) => Promise<void> }> = ({ node, level, onSync }) => {
  const [isOpen, setIsOpen] = useState(level < 1);
  const [isLocalSyncing, setIsLocalSyncing] = useState(false);
  const hasChildren = node.children && node.children.length > 0;

  // Determine if node is currently syncing based on local state OR backend status
  const isSyncing = isLocalSyncing || node.status === 'syncing' || node.status === 'metadata';

  const getIcon = () => {
    switch (node.type) {
      case 'project': return <Database size={14} className="text-blue" />;
      case 'folder': return <Folder size={14} className="text-orange" />;
      case 'channel': return <MessageSquare size={14} className="text-emerald" />;
      default: return null;
    }
  };

  const handleSyncClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!onSync) return;
    setIsLocalSyncing(true);
    try {
      await onSync(node.id);
    } finally {
      setIsLocalSyncing(false);
    }
  };

  return (
    <>
      <div className={`tree-row level-${level} ${node.type} ${isSyncing ? 'syncing' : ''}`} onClick={() => hasChildren && setIsOpen(!isOpen)}>
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
            <Pacman active={isSyncing || node.percentage > 0} />
            <div className="progress-mini">
              <div className="progress-mini-fill" style={{ 
                width: `${node.percentage}%`, 
                backgroundColor: isSyncing ? '#3b82f6' : undefined,
                transition: 'width 0.5s ease-out'
              }}></div>
            </div>
            <span className="pct-text">{isSyncing && node.percentage === 0 ? '⧗' : `${node.percentage}%`}</span>
          </div>
        </div>

        <div className="tree-col files-col">
          {isSyncing ? (
            <span className="text-blue" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Activity size={12} className="spin" />
              {node.status === 'metadata' ? 'подготовка...' : 'синхронизация...'}
            </span>
          ) : `${node.files.toLocaleString()} msg`}
        </div>

        <div className="tree-col change-col">
          {isSyncing ? '🔄 в процессе' : (node.last_change ? new Date(node.last_change).toLocaleTimeString() : '—')}
        </div>

        {node.type === 'folder' && onSync && (
          <button
            className="sync-btn-tree"
            onClick={handleSyncClick}
            disabled={isSyncing}
            title="Синхронизировать папку"
            style={{
              background: isSyncing ? '#3b82f6' : '#10b981',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 12px',
              cursor: isSyncing ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              opacity: 1,
              transition: 'background-color 0.2s',
              position: 'relative'
            }}
          >
            {isSyncing ? (
              <Activity size={14} color="white" className="spin" />
            ) : (
              <Play size={14} color="white" />
            )}
          </button>
        )}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .tree-row.syncing {
          background: rgba(59, 130, 246, 0.1);
        }
      `}</style>
      
      {isOpen && hasChildren && (
        <div className="tree-children">
          {node.children!.map(child => (
            <TreeRow key={child.id} node={child} level={level + 1} onSync={onSync} />
          ))}
        </div>
      )}
    </>
  );
};

export const DataFlowTree: React.FC<{ tree: TreeNode[]; onSync?: (folderId: string) => Promise<void> }> = ({ tree, onSync }) => {
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
          <TreeRow key={node.id} node={node} level={0} onSync={onSync} />
        ))}
      </div>
    </div>
  );
};

export const SystemFlow: React.FC<{ metrics: any }> = ({ metrics }) => {
  const throughput = metrics?.throughput || { ingestion: 0, extraction: 0, embeddings: 0 };
  
  const getMetric = (name: string, type: 'cpu' | 'memory') => {
    const data = metrics?.[name]?.[type];
    if (!data || data.length === 0) return '—';
    const val = data[data.length - 1].value;
    return type === 'cpu' ? `${val}%` : `${Math.round(val)}MB`;
  };

  const Connector = ({ value, unit, label, reverse }: any) => {
    // Calculate animation speed: more throughput = faster particles
    const speed = value > 0 ? Math.max(0.4, 2 - (value / 500)) : 0;
    const opacity = value > 0 ? 1 : 0.2;

    return (
      <div className="flow-connector vertical-align" style={{ opacity }}>
        <div className="connector-label-top">{value} {unit}</div>
        <div 
          className={`flow-particles ${reverse ? 'reverse' : ''}`} 
          style={{ animationDuration: `${speed}s`, display: value > 0 ? 'block' : 'none' }}
        ></div>
        <div className="connector-label-bottom">{label}</div>
      </div>
    );
  };

  const Node = ({ id, label, icon: Icon, color }: any) => (
    <div className={`flow-node ${color}`}>
      <div className="node-metrics">
        <span>CPU: {getMetric(id, 'cpu')}</span>
        <span>MEM: {getMetric(id, 'memory')}</span>
      </div>
      <Icon size={20} />
      <span className="node-label">{label}</span>
      <div className={`node-status online`}></div>
    </div>
  );

  return (
    <div className="system-flow-container serpent-card">
      <div className="flow-grid">
        {/* Source */}
        <div className="flow-section">
          <div className="section-label">Data Source</div>
          <div className="flow-node blue pulse">
            <Cloud size={24} />
            <span>Telegram API</span>
            <div className="node-status online"></div>
          </div>
        </div>

        <Connector 
          value={throughput.ingestion} 
          unit="msg/m" 
          label="Ingestion" 
        />

        {/* Backend / Conductor */}
        <div className="flow-section">
          <div className="section-label">Conductor</div>
          <div className="flow-stack">
            <Node id="crm-app" label="App API" icon={Activity} color="purple" />
            <Node id="crm-beat" label="Scheduler" icon={Zap} color="purple" />
          </div>
        </div>

        <Connector 
          value={throughput.extraction} 
          unit="tasks/m" 
          label="AI Process" 
        />

        {/* Workers */}
        <div className="flow-section">
          <div className="section-label">Workers</div>
          <div className="flow-stack">
            <Node id="crm-worker-connectors" label="Connectors" icon={Cpu} color="orange" />
            <Node id="crm-worker-processing" label="Processor" icon={Cpu} color="orange" />
          </div>
        </div>

        <Connector 
          value={throughput.embeddings} 
          unit="vec/m" 
          label="Vectors" 
        />

        {/* Infrastructure */}
        <div className="flow-section">
          <div className="section-label">Infrastructure</div>
          <div className="flow-stack">
            <div className="flow-row">
              <Node id="crm-postgres" label="Postgres" icon={HardDrive} color="emerald" />
              <Node id="crm-redis" label="Redis" icon={Database} color="emerald" />
            </div>
            <div className="flow-row">
              <Node id="crm-whisper" label="Whisper" icon={Zap} color="blue" />
              <Node id="crm-prometheus" label="Prometheus" icon={Activity} color="blue" />
            </div>
          </div>
        </div>
      </div>

      <div className="flow-description">
        <div className="flow-info">
          <Zap size={14} className="text-venom" />
          <span>Active Streams: <strong>{throughput.ingestion > 0 ? 'High Activity' : 'Standby'}</strong></span>
        </div>
        <div className="flow-info">
          <Activity size={14} className="text-blue" />
          <span>Aggregate Load: <strong>{throughput.extraction > 10 ? 'Heavy AI' : 'Normal'}</strong></span>
        </div>
      </div>
    </div>
  );
};
