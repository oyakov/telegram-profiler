import React, { useState } from 'react';
import {
  Database, Folder, MessageSquare, ChevronRight, ChevronDown,
  Cpu, HardDrive, Zap, Cloud, Activity, Play, BrainCircuit, Layers
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
  oldest_message_date?: string;
}

function formatDepth(isoDate: string | undefined): string {
  if (!isoDate) return '—';
  const ms = Date.now() - new Date(isoDate).getTime();
  const days = Math.floor(ms / 86_400_000);
  if (days < 1) return 'сегодня';
  if (days < 30) return `${days} дн. назад`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} мес. назад`;
  const years = Math.floor(months / 12);
  const rem = months % 12;
  if (rem === 0) return `${years} ${years === 1 ? 'год' : years < 5 ? 'года' : 'лет'} назад`;
  return `${years}г ${rem}м назад`;
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
  const [isOpen, setIsOpen] = useState(false);
  const [isLocalSyncing, setIsLocalSyncing] = useState(false);
  const hasChildren = node.children && node.children.length > 0;

  // Determine if node is currently syncing based on local state OR backend status
  const isSyncing = isLocalSyncing || node.status === 'syncing' || node.status === 'metadata' || node.status === 'reconciling';

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
            <span className="pct-text">{isSyncing && node.percentage === 0 ? '⧗' : formatDepth(node.oldest_message_date)}</span>
          </div>
        </div>
<div className="tree-col files-col" style={{ flexDirection: 'column', alignItems: 'flex-end', gap: '2px' }}>
  <div style={{ fontWeight: 600 }}>{node.files.toLocaleString()} msg</div>
  {isSyncing && (
    <span className="text-blue" style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
      <Activity size={10} className="spin" />
      {node.status === 'metadata' ? 'подготовка...' : 
       node.status === 'reconciling' ? 'сверка...' : 'синхронизация...'}
    </span>
  )}
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

// ─── SystemFlow v2 ────────────────────────────────────────────────────────────

const SF_STYLES = `
  @keyframes particleFlow {
    0%   { transform: translateX(-48px); opacity: 0; }
    8%   { opacity: 1; }
    92%  { opacity: 1; }
    100% { transform: translateX(calc(var(--track-w, 160px) + 48px)); opacity: 0; }
  }
  @keyframes sfPulse {
    0%, 100% { box-shadow: 0 0 6px currentColor; opacity: 1; }
    50%       { box-shadow: 0 0 14px currentColor; opacity: 0.7; }
  }
  @keyframes sfNodeGlow {
    0%, 100% { box-shadow: var(--node-glow-base); }
    50%       { box-shadow: var(--node-glow-hover); }
  }
  @keyframes sfOrbit {
    from { transform: rotate(0deg) translateX(12px) rotate(0deg); }
    to   { transform: rotate(360deg) translateX(12px) rotate(-360deg); }
  }
  .sf-wrap { padding: 36px 28px 24px; background: rgba(10,18,35,0.5); backdrop-filter: blur(12px); }
  .sf-grid { display: flex; align-items: center; gap: 0; margin-bottom: 32px; }
  .sf-section { display: flex; flex-direction: column; align-items: center; gap: 12px; flex-shrink: 0; }
  .sf-section-label {
    font-size: 0.65rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: 1.5px; color: rgba(148,163,184,0.5); white-space: nowrap;
  }
  .sf-stack { display: flex; flex-direction: column; gap: 10px; }
  .sf-node {
    display: flex; flex-direction: column; align-items: center; gap: 7px;
    padding: 14px 16px; border-radius: 14px; min-width: 120px;
    position: relative; transition: transform 0.2s ease, box-shadow 0.2s ease;
    border: 1px solid; cursor: default;
  }
  .sf-node:hover { transform: translateY(-2px); }
  .sf-node-icon { display: flex; align-items: center; justify-content: center; }
  .sf-node-label { font-size: 0.82rem; font-weight: 700; white-space: nowrap; }
  .sf-node-metrics {
    position: absolute; top: 5px; left: 7px;
    font-size: 7.5px; font-family: monospace; line-height: 1.4;
    color: rgba(148,163,184,0.55);
  }
  .sf-node-dot {
    position: absolute; top: 8px; right: 8px;
    width: 6px; height: 6px; border-radius: 50%;
  }

  /* Particle stream track */
  .sf-stream { flex: 1; min-width: 60px; display: flex; flex-direction: column; align-items: center; gap: 0; position: relative; }
  .sf-stream-badge {
    font-size: 10.5px; font-weight: 800; padding: 3px 10px; border-radius: 6px;
    border: 1px solid; white-space: nowrap; margin-bottom: 10px;
    letter-spacing: 0.3px; transition: all 0.4s ease;
  }
  .sf-stream-track {
    width: 100%; height: 4px; border-radius: 2px;
    position: relative; overflow: hidden;
  }
  .sf-stream-particle {
    position: absolute; top: 0; left: 0;
    width: 48px; height: 4px; border-radius: 2px;
    animation: particleFlow linear infinite;
  }
  .sf-stream-label {
    font-size: 8px; text-transform: uppercase; letter-spacing: 1px;
    color: rgba(148,163,184,0.4); margin-top: 10px; white-space: nowrap;
  }

  /* AI Provider card */
  .sf-ai-branch { display: flex; flex-direction: column; align-items: center; margin-top: 14px; gap: 0; }
  .sf-ai-vline { width: 2px; height: 22px; border-radius: 1px; opacity: 0.5; }
  .sf-ai-card {
    border: 1px solid; border-radius: 14px; padding: 14px 20px;
    display: flex; flex-direction: column; align-items: center; gap: 6px;
    position: relative; min-width: 180px; transition: box-shadow 0.3s ease;
  }
  .sf-ai-label { font-size: 0.9rem; font-weight: 800; }
  .sf-ai-model { font-size: 9.5px; opacity: 0.55; text-align: center; max-width: 160px; word-break: break-all; }
  .sf-ai-stats { display: flex; gap: 12px; margin-top: 4px; font-size: 11px; font-family: monospace; }
  .sf-ai-avail {
    position: absolute; top: 8px; right: 10px;
    display: flex; align-items: center; gap: 4px;
    font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;
  }
  .sf-ai-dot { width: 6px; height: 6px; border-radius: 50%; }

  .sf-footer {
    display: flex; gap: 24px; justify-content: center; flex-wrap: wrap;
    border-top: 1px solid rgba(255,255,255,0.06); padding-top: 18px;
  }
  .sf-footer-item { display: flex; align-items: center; gap: 7px; font-size: 0.85rem; }
  .sf-footer-item strong { font-weight: 700; }
`;

interface EmbedProvider { provider: string; available: boolean; model: string; dimensions: number; speed_vec_per_min: number; }

const SFParticleStream: React.FC<{
  value: number; unit: string; label: string; color: string;
}> = ({ value, unit, label, color }) => {
  const active = value > 0;
  const duration = active ? Math.max(0.7, 2.6 - value / 300) : 2;
  const count  = active ? Math.min(7, Math.max(2, Math.floor(value / 80) + 2)) : 0;

  return (
    <div className="sf-stream">
      <div
        className="sf-stream-badge"
        style={{
          color: active ? color : 'rgba(148,163,184,0.4)',
          borderColor: active ? `${color}55` : 'rgba(255,255,255,0.08)',
          background: active ? `${color}12` : 'transparent',
          boxShadow: active ? `0 0 14px ${color}22` : 'none',
        }}
      >
        {active ? value.toLocaleString() : '—'}&nbsp;
        <span style={{ fontWeight: 400, opacity: 0.65 }}>{unit}</span>
      </div>

      <div
        className="sf-stream-track"
        style={{ background: active ? `${color}18` : 'rgba(255,255,255,0.05)' }}
      >
        {Array.from({ length: count }).map((_, i) => (
          <div
            key={i}
            className="sf-stream-particle"
            style={{
              background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
              boxShadow: `0 0 6px ${color}bb`,
              animationDuration: `${duration}s`,
              animationDelay: `${-(i / count) * duration}s`,
            }}
          />
        ))}
      </div>

      <div className="sf-stream-label">{label}</div>
    </div>
  );
};

const SFNode: React.FC<{
  id?: string; label: string; icon: React.ElementType;
  color: string; metrics?: { cpu: string; mem: string };
  pulse?: boolean; children?: React.ReactNode;
}> = ({ label, icon: Icon, color, metrics, pulse, children }) => (
  <div
    className="sf-node"
    style={{
      borderColor: `${color}55`,
      background: `${color}0d`,
      boxShadow: `0 0 22px ${color}18`,
      color,
    }}
  >
    {metrics && (
      <div className="sf-node-metrics">
        <div>CPU: {metrics.cpu}</div>
        <div>MEM: {metrics.mem}</div>
      </div>
    )}
    <div
      className="sf-node-dot"
      style={{
        background: '#10b981',
        boxShadow: '0 0 6px #10b981',
        animation: pulse ? 'sfPulse 2s ease-in-out infinite' : 'sfPulse 3s ease-in-out infinite',
      }}
    />
    <div className="sf-node-icon"><Icon size={22} /></div>
    <span className="sf-node-label">{label}</span>
    {children}
  </div>
);

const SFAIProviderCard: React.FC<{ ep: EmbedProvider }> = ({ ep }) => {
  const isLM = ep.provider === 'lmstudio';
  const color = isLM ? '#a855f7' : '#3b82f6';
  const name  = isLM ? 'LMStudio' : 'Gemini';
  const Icon  = isLM ? BrainCircuit : Cloud;
  const shortModel = ep.model.length > 24 ? ep.model.slice(0, 22) + '…' : ep.model;
  const speedColor = ep.speed_vec_per_min > 0 ? '#10b981' : 'rgba(148,163,184,0.5)';

  return (
    <div
      className="sf-ai-card"
      style={{
        borderColor: `${color}50`,
        background: `${color}0c`,
        boxShadow: ep.available ? `0 0 30px ${color}22` : 'none',
        color,
      }}
    >
      <div className="sf-ai-avail" style={{ color: ep.available ? '#10b981' : '#ef4444' }}>
        <div
          className="sf-ai-dot"
          style={{
            background: ep.available ? '#10b981' : '#ef4444',
            boxShadow: `0 0 6px ${ep.available ? '#10b981' : '#ef4444'}`,
            animation: ep.available ? 'sfPulse 2s infinite' : 'none',
          }}
        />
        {ep.available ? 'online' : 'offline'}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Icon size={20} />
        <span className="sf-ai-label">{name}</span>
      </div>
      <div className="sf-ai-model">{shortModel}</div>

      <div className="sf-ai-stats">
        <span style={{ color: `${color}cc` }}>{ep.dimensions}-dim</span>
        <span style={{ color: speedColor }}>
          {ep.speed_vec_per_min > 0 ? `${ep.speed_vec_per_min.toLocaleString()} vec/min` : 'idle'}
        </span>
      </div>
    </div>
  );
};

export const SystemFlow: React.FC<{ metrics: any; embedProvider?: EmbedProvider }> = ({ metrics, embedProvider }) => {
  const lastValid = React.useRef<any>(null);
  const m = React.useMemo(() => {
    if (metrics?.throughput) { lastValid.current = metrics; return metrics; }
    return lastValid.current || {};
  }, [metrics]);

  const tp = m?.throughput || { ingestion: 0, extraction: 0, embeddings: 0 };

  const getMetric = (id: string, type: 'cpu' | 'memory') => {
    const d = m?.[id]?.[type];
    if (!d?.length) return '—';
    const v = d[d.length - 1].value;
    return type === 'cpu' ? `${v}%` : `${Math.round(v)}MB`;
  };
  const nodeMetrics = (id: string) => ({ cpu: getMetric(id, 'cpu'), mem: getMetric(id, 'memory') });

  const embedColor = embedProvider?.provider === 'lmstudio' ? '#a855f7' : '#3b82f6';
  const vecSpeed   = embedProvider?.speed_vec_per_min ?? tp.embeddings ?? 0;

  return (
    <div className="sf-wrap serpent-card">
      <style>{SF_STYLES}</style>

      <div className="sf-grid">

        {/* 1. Data Source */}
        <div className="sf-section">
          <div className="sf-section-label">Data Source</div>
          <SFNode label="Telegram API" icon={Cloud} color="#3b82f6" pulse metrics={nodeMetrics('crm-telegram')} />
        </div>

        <SFParticleStream value={tp.ingestion} unit="msg/min" label="Ingestion" color="#3b82f6" />

        {/* 2. Conductor */}
        <div className="sf-section">
          <div className="sf-section-label">Conductor</div>
          <div className="sf-stack">
            <SFNode label="App API"    icon={Activity} color="#a855f7" metrics={nodeMetrics('crm-app')} />
            <SFNode label="Scheduler"  icon={Zap}      color="#a855f7" metrics={nodeMetrics('crm-beat')} />
          </div>
        </div>

        <SFParticleStream value={tp.extraction} unit="tasks/m" label="AI Process" color="#a855f7" />

        {/* 3. Workers + AI branch */}
        <div className="sf-section">
          <div className="sf-section-label">Workers</div>
          <div className="sf-stack">
            <SFNode label="Connectors" icon={Cpu} color="#f59e0b" metrics={nodeMetrics('crm-worker-connectors')} />
            <SFNode label="Processor"  icon={Cpu} color="#f59e0b" metrics={nodeMetrics('crm-worker-processing')} />
          </div>
          {embedProvider && (
            <div className="sf-ai-branch">
              <div className="sf-ai-vline" style={{ background: embedColor }} />
              <SFAIProviderCard ep={embedProvider} />
            </div>
          )}
        </div>

        <SFParticleStream value={vecSpeed} unit="vec/min" label="Vectors" color={embedColor} />

        {/* 4. Storage */}
        <div className="sf-section">
          <div className="sf-section-label">Storage</div>
          <div className="sf-stack">
            <div style={{ display: 'flex', gap: 10 }}>
              <SFNode label="Postgres" icon={HardDrive} color="#10b981" metrics={nodeMetrics('crm-postgres')} />
              <SFNode label="Redis"    icon={Database}  color="#10b981" metrics={nodeMetrics('crm-redis')} />
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <SFNode label="Whisper"     icon={Zap}      color="#38bdf8" metrics={nodeMetrics('crm-whisper')} />
              <SFNode label="Prometheus"  icon={Layers}   color="#38bdf8" metrics={nodeMetrics('crm-prometheus')} />
            </div>
          </div>
        </div>

      </div>

      {/* Footer */}
      <div className="sf-footer">
        <div className="sf-footer-item">
          <Zap size={14} color="#10b981" />
          <span style={{ color: 'rgba(148,163,184,0.7)' }}>
            Active Streams: <strong style={{ color: '#10b981' }}>{tp.ingestion > 0 ? 'High Activity' : 'Standby'}</strong>
          </span>
        </div>
        <div className="sf-footer-item">
          <Activity size={14} color="#3b82f6" />
          <span style={{ color: 'rgba(148,163,184,0.7)' }}>
            Load: <strong style={{ color: '#3b82f6' }}>{tp.extraction > 10 ? 'Heavy AI' : 'Normal'}</strong>
          </span>
        </div>
        {embedProvider && (
          <div className="sf-footer-item">
            <BrainCircuit size={14} color={embedColor} />
            <span style={{ color: 'rgba(148,163,184,0.7)' }}>
              Embeddings:&nbsp;
              <strong style={{ color: embedProvider.available ? '#10b981' : '#ef4444' }}>
                {embedProvider.provider === 'lmstudio' ? 'LMStudio' : 'Gemini'}&nbsp;
                {embedProvider.available ? '●' : '○'}
              </strong>
              {vecSpeed > 0 && <span style={{ color: embedColor }}>&nbsp;· {vecSpeed.toLocaleString()} vec/min</span>}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
