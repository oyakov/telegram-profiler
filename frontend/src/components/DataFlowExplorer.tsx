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

// ─── SystemFlow v3 — SVG graph with animateMotion particles ──────────────────

interface EmbedProvider { provider: string; available: boolean; model: string; dimensions: number; speed_vec_per_min: number; }

// ── Canvas & node layout ────────────────────────────────────────────────────
const CW = 860, CH = 480;

interface NodeDef { x:number; y:number; w:number; h:number; color:string; name:string; sub:string; ext?:boolean; }

const NODES: Record<string, NodeDef> = {
  telegram:   { x:118,  y:82,  w:132, h:60, color:'#3b82f6', name:'Telegram',          sub:'External API',    ext:true },
  lmstudio:   { x:742,  y:82,  w:144, h:60, color:'#a855f7', name:'LMStudio',           sub:'Embedding model', ext:true },
  app:        { x:215,  y:238, w:138, h:60, color:'#7c3aed', name:'crm-app',            sub:'FastAPI · uvicorn' },
  beat:       { x:430,  y:385, w:130, h:60, color:'#7c3aed', name:'crm-beat',           sub:'Celery Beat' },
  processor:  { x:645,  y:238, w:154, h:60, color:'#f59e0b', name:'crm-worker',         sub:'processing' },
  connectors: { x:215,  y:385, w:154, h:60, color:'#f59e0b', name:'crm-worker',         sub:'connectors' },
  redis:      { x:430,  y:238, w:130, h:60, color:'#10b981', name:'crm-redis',          sub:'Broker · Cache' },
  postgres:   { x:645,  y:385, w:142, h:60, color:'#10b981', name:'crm-postgres',       sub:'PostgreSQL · pgvector' },
};

// ── Geometry helpers ─────────────────────────────────────────────────────────
function borderPt(n: NodeDef, tx: number, ty: number, gap = 7) {
  const dx = tx - n.x, dy = ty - n.y;
  const ang = Math.atan2(dy, dx);
  const hw = n.w / 2 + gap, hh = n.h / 2 + gap;
  const t = Math.min(
    Math.abs(Math.cos(ang)) > 1e-6 ? hw / Math.abs(Math.cos(ang)) : 1e9,
    Math.abs(Math.sin(ang)) > 1e-6 ? hh / Math.abs(Math.sin(ang)) : 1e9,
  );
  return { x: n.x + Math.cos(ang) * t, y: n.y + Math.sin(ang) * t };
}

function edgePath(a: NodeDef, b: NodeDef) {
  const p1 = borderPt(a, b.x, b.y);
  const p2 = borderPt(b, a.x, a.y);
  const mx = (p1.x + p2.x) / 2, my = (p1.y + p2.y) / 2;
  const dist = Math.hypot(p2.x - p1.x, p2.y - p1.y);
  const c = Math.min(28, dist * 0.18);
  const px = dist > 1 ? -(p2.y - p1.y) / dist * c : 0;
  const py = dist > 1 ?  (p2.x - p1.x) / dist * c : 0;
  const cp = { x: mx + px, y: my + py };
  return {
    d: `M ${p1.x.toFixed(1)} ${p1.y.toFixed(1)} Q ${cp.x.toFixed(1)} ${cp.y.toFixed(1)} ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`,
    lx: cp.x, ly: cp.y,
  };
}

// ── Edge renderer ────────────────────────────────────────────────────────────
interface EdgeSpec { from:string; to:string; color:string; label?:string; speed?:number; active?:boolean; }

const GraphEdge: React.FC<{ spec: EdgeSpec }> = ({ spec }) => {
  const a = NODES[spec.from], b = NODES[spec.to];
  if (!a || !b) return null;
  const { d, lx, ly } = edgePath(a, b);
  const active = spec.active !== false;
  const spd = spec.speed ?? 0;
  const count = active ? Math.min(5, Math.max(1, Math.floor(spd / 180) + 1)) : 0;
  const dur   = active ? Math.max(0.9, 2.8 - spd / 400) : 2;

  return (
    <g>
      <path d={d} fill="none" stroke={spec.color}
        strokeWidth={active ? 1.6 : 1}
        strokeOpacity={active ? 0.45 : 0.18}
        strokeDasharray={active ? undefined : '5 5'} />
      {Array.from({ length: count }).map((_, i) => (
        <circle key={i} r={3.2} fill={spec.color}
          style={{ filter: `drop-shadow(0 0 4px ${spec.color})` }}>
          <animateMotion path={d} dur={`${dur}s`} repeatCount="indefinite"
            begin={`${-((i / count) * dur).toFixed(2)}s`} />
        </circle>
      ))}
      {spec.label && (
        <text x={lx} y={ly - 6} textAnchor="middle"
          fontSize={8.5} fontFamily="ui-monospace,monospace" fontWeight="700"
          fill={spec.color} fillOpacity={0.75}>
          {spec.label}
        </text>
      )}
    </g>
  );
};

// ── Node card (foreignObject) ────────────────────────────────────────────────
const GraphNode: React.FC<{ id: string; ep?: EmbedProvider; metrics: any }> = ({ id, ep, metrics }) => {
  const n = NODES[id];
  if (!n) return null;

  const getM = (type: 'cpu'|'memory') => {
    const d = metrics?.[id]?.[type];
    if (!d?.length) return null;
    const v = d[d.length-1].value;
    return type === 'cpu' ? `${v}%` : `${Math.round(v)}M`;
  };

  const isLM = id === 'lmstudio';
  const dotColor = isLM ? (ep?.available ? '#10b981' : '#ef4444') : '#10b981';

  const sub = isLM && ep
    ? `${ep.dimensions}-dim · ${ep.speed_vec_per_min > 0 ? ep.speed_vec_per_min + ' v/m' : 'idle'}`
    : n.sub;

  const providerName = isLM && ep
    ? (ep.provider === 'lmstudio' ? 'LMStudio' : 'Gemini')
    : n.name;

  return (
    <foreignObject x={n.x - n.w/2} y={n.y - n.h/2} width={n.w} height={n.h} style={{ overflow: 'visible' }}>
      <div style={{
        width: '100%', height: '100%', boxSizing: 'border-box',
        background: n.ext ? `${n.color}15` : `${n.color}0e`,
        border: `1px solid ${n.color}${n.ext ? '65' : '48'}`,
        borderRadius: 11,
        boxShadow: `0 0 ${n.ext ? 22 : 16}px ${n.color}${n.ext ? '28' : '1a'}`,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: '5px 8px', gap: 3, position: 'relative',
        fontFamily: 'system-ui, sans-serif',
      }}>
        {/* status dot */}
        <div style={{
          position: 'absolute', top: 6, right: 7,
          width: 6, height: 6, borderRadius: '50%',
          background: dotColor, boxShadow: `0 0 7px ${dotColor}`,
        }} />
        {/* cpu/mem */}
        {!n.ext && (getM('cpu') || getM('memory')) && (
          <div style={{ position: 'absolute', top: 4, left: 6, fontSize: 7,
            fontFamily: 'monospace', color: 'rgba(148,163,184,0.5)', lineHeight: 1.4 }}>
            {getM('cpu') && <div>CPU {getM('cpu')}</div>}
            {getM('memory') && <div>MEM {getM('memory')}</div>}
          </div>
        )}
        <div style={{ fontSize: 12, fontWeight: 700, color: n.color, whiteSpace: 'nowrap' }}>
          {providerName}
        </div>
        <div style={{ fontSize: 9, color: 'rgba(148,163,184,0.5)', whiteSpace: 'nowrap' }}>
          {sub}
        </div>
      </div>
    </foreignObject>
  );
};

// ── Main component ────────────────────────────────────────────────────────────
export const SystemFlow: React.FC<{ metrics: any; embedProvider?: EmbedProvider }> = ({ metrics, embedProvider }) => {
  const lastValid = React.useRef<any>(null);
  const m = React.useMemo(() => {
    if (metrics?.throughput) { lastValid.current = metrics; return metrics; }
    return lastValid.current || {};
  }, [metrics]);

  const tp = m?.throughput || { ingestion: 0, extraction: 0, embeddings: 0 };
  const vecSpeed   = embedProvider?.speed_vec_per_min ?? tp.embeddings ?? 0;
  const embedColor = embedProvider?.provider === 'lmstudio' ? '#a855f7' : '#3b82f6';

  // Update lmstudio node color dynamically
  if (embedProvider) {
    NODES.lmstudio = { ...NODES.lmstudio, color: embedColor };
  }

  const EDGES: EdgeSpec[] = [
    // Telegram ↔ app/connectors
    { from:'telegram',   to:'app',        color:'#3b82f6', label: tp.ingestion > 0 ? `${Math.round(tp.ingestion)} msg/m` : 'msgs',  speed: tp.ingestion * 8 + 60 },
    { from:'connectors', to:'telegram',   color:'#60a5fa', label:'fetch',        speed: 80,  active: true },
    // App → infra
    { from:'app',        to:'redis',      color:'#f59e0b', label:'queue',        speed: 200, active: true },
    { from:'app',        to:'postgres',   color:'#10b981', label:'SQL',          speed: 150, active: true },
    // Beat → Redis
    { from:'beat',       to:'redis',      color:'#c084fc', label:'dispatch',     speed: 80,  active: true },
    // Redis → workers
    { from:'redis',      to:'processor',  color:'#f59e0b', label:'tasks',        speed: vecSpeed > 0 ? 280 : 120, active: true },
    { from:'redis',      to:'connectors', color:'#f59e0b', label:'tasks',        speed: 120, active: true },
    // Worker → external
    { from:'processor',  to:'lmstudio',   color: embedColor, label: vecSpeed > 0 ? `${vecSpeed} v/m` : 'embed', speed: vecSpeed, active: vecSpeed > 0 },
    // Workers → postgres
    { from:'processor',  to:'postgres',   color:'#10b981', label:'write',        speed: 180, active: true },
    { from:'connectors', to:'postgres',   color:'#10b981', label:'write',        speed: 120, active: true },
  ];

  return (
    <div style={{ padding: '24px 20px 18px', background: 'rgba(10,18,35,0.5)', backdropFilter: 'blur(12px)', borderRadius: 'inherit' }}>
      <svg
        viewBox={`0 0 ${CW} ${CH}`}
        style={{ width: '100%', height: 'auto', display: 'block', overflow: 'visible' }}
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Subtle dot grid */}
        <defs>
          <pattern id="sfgrid" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
            <circle cx="0.5" cy="0.5" r="0.5" fill="rgba(255,255,255,0.07)" />
          </pattern>
        </defs>
        <rect width={CW} height={CH} fill="url(#sfgrid)" />

        {/* Section labels */}
        {[
          { label: 'EXTERNAL',  x: 118 },
          { label: 'APP LAYER', x: 215 },
          { label: 'BROKER',    x: 430 },
          { label: 'WORKERS',   x: 645 },
        ].map(({ label, x }) => (
          <text key={label} x={x} y={22} textAnchor="middle"
            fontSize={9} fontFamily="ui-monospace,monospace" fontWeight="800"
            fill="rgba(148,163,184,0.35)" letterSpacing="1.5">
            {label}
          </text>
        ))}

        {/* Edges (drawn first, behind nodes) */}
        {EDGES.map((spec, i) => <GraphEdge key={i} spec={spec} />)}

        {/* Nodes (drawn on top) */}
        {Object.keys(NODES).map(id => (
          <GraphNode key={id} id={id} ep={embedProvider} metrics={m} />
        ))}
      </svg>

      {/* Footer */}
      <div style={{ display:'flex', gap:24, justifyContent:'center', flexWrap:'wrap',
        borderTop:'1px solid rgba(255,255,255,0.06)', paddingTop:14, marginTop:10 }}>
        <div style={{ display:'flex', alignItems:'center', gap:7, fontSize:'0.82rem' }}>
          <Zap size={13} color="#10b981" />
          <span style={{ color:'rgba(148,163,184,0.65)' }}>
            Ingestion:&nbsp;<strong style={{ color:'#10b981' }}>
              {tp.ingestion > 0 ? `${Math.round(tp.ingestion)} msg/min` : 'Standby'}
            </strong>
          </span>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:7, fontSize:'0.82rem' }}>
          <Database size={13} color="#10b981" />
          <span style={{ color:'rgba(148,163,184,0.65)' }}>
            6 containers running
          </span>
        </div>
        {embedProvider && (
          <div style={{ display:'flex', alignItems:'center', gap:7, fontSize:'0.82rem' }}>
            <BrainCircuit size={13} color={embedColor} />
            <span style={{ color:'rgba(148,163,184,0.65)' }}>
              {embedProvider.provider === 'lmstudio' ? 'LMStudio' : 'Gemini'}&nbsp;
              <strong style={{ color: embedProvider.available ? '#10b981' : '#ef4444' }}>
                {embedProvider.available ? '● online' : '○ offline'}
              </strong>
              {vecSpeed > 0 && <span style={{ color: embedColor }}>&nbsp;· {vecSpeed.toLocaleString()} vec/min</span>}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
