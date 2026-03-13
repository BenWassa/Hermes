import { Activity, TrendingDown, TrendingUp, Minus } from 'lucide-react';

const TREND_THEMES = {
  up: {
    text: 'text-emerald-400',
    stroke: '#34d399',
    glow: 'drop-shadow-[0_0_8px_rgba(52,211,153,0.6)]',
    bgFill: 'from-emerald-400/20',
    icon: TrendingUp
  },
  down: {
    text: 'text-rose-400',
    stroke: '#fb7185',
    glow: 'drop-shadow-[0_0_8px_rgba(251,113,133,0.6)]',
    bgFill: 'from-rose-400/20',
    icon: TrendingDown
  },
  flat: {
    text: 'text-slate-400',
    stroke: '#94a3b8',
    glow: 'drop-shadow-[0_0_8px_rgba(148,163,184,0.6)]',
    bgFill: 'from-slate-400/20',
    icon: Minus
  }
};

function normalizeSeries(data) {
  if (!Array.isArray(data)) return [];
  return data.map((value) => Number(value)).filter((value) => Number.isFinite(value));
}

function buildPolylinePoints(data) {
  const numeric = normalizeSeries(data);
  if (numeric.length === 0) return '';

  const min = Math.min(...numeric);
  const max = Math.max(...numeric);
  const range = max - min || 1;

  return numeric
    .map((value, index) => {
      const x = numeric.length === 1 ? 50 : (index / (numeric.length - 1)) * 100;
      const y = 30 - ((value - min) / range) * 24 - 3;
      return `${x},${y}`;
    })
    .join(' ');
}

function buildFillPath(points) {
  if (!points) return '';
  return `M 0,30 L ${points
    .split(' ')
    .map((point) => point.replace(',', ','))
    .join(' L ')} L 100,30 Z`;
}

export function MacroSparklineWidget({
  title = 'Macro Trend',
  metric = '',
  currentValue = '',
  trendValue = '',
  trendDirection = 'flat',
  data = [],
  details = ''
}) {
  const theme = TREND_THEMES[trendDirection] || TREND_THEMES.flat;
  const TrendIcon = theme.icon;
  const points = buildPolylinePoints(data);
  const fillPath = buildFillPath(points);
  const gradientId = `gradient-${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;

  return (
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-5 shadow-[0_8px_30px_rgb(0,0,0,0.12)] relative overflow-hidden group">
      <div className={`absolute -top-10 -right-10 w-32 h-32 rounded-full blur-3xl opacity-20 bg-gradient-to-br ${theme.bgFill} to-transparent`} />

      <div className="flex justify-between items-start mb-4 relative z-10 gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <Activity size={16} className="text-cyan-400 shrink-0" />
          <h3 className="text-[12px] font-bold uppercase tracking-widest text-cyan-400 truncate">{title}</h3>
        </div>
        {metric ? (
          <div className="text-[10px] font-mono text-slate-500 uppercase tracking-widest bg-slate-900/50 px-2 py-0.5 rounded-[3px] border border-white/5 shrink-0">
            {metric}
          </div>
        ) : null}
      </div>

      <div className="flex items-end gap-3 mb-6 relative z-10">
        <div className="text-3xl font-extrabold text-white tracking-tight leading-none">{currentValue}</div>
        {trendValue ? (
          <div className={`flex items-center gap-1 text-[13px] font-mono font-bold mb-0.5 ${theme.text}`}>
            <TrendIcon size={14} strokeWidth={2.5} />
            {trendValue}
          </div>
        ) : null}
      </div>

      <div className="w-full h-14 relative z-10">
        <svg viewBox="0 0 100 30" preserveAspectRatio="none" className={`w-full h-full overflow-visible ${theme.glow}`}>
          <defs>
            <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={theme.stroke} stopOpacity="0.3" />
              <stop offset="100%" stopColor={theme.stroke} stopOpacity="0" />
            </linearGradient>
          </defs>

          {fillPath ? <path d={fillPath} fill={`url(#${gradientId})`} className="transition-all duration-700 ease-in-out" /> : null}
          {points ? (
            <polyline
              fill="none"
              stroke={theme.stroke}
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              points={points}
              className="transition-all duration-700 ease-in-out"
            />
          ) : null}
        </svg>
      </div>

      {details ? (
        <div className="mt-4 pt-4 border-t border-white/10 text-[12px] text-slate-400 leading-relaxed font-medium relative z-10">
          <span className="text-cyan-500/50 font-mono mr-2">///</span>
          {details}
        </div>
      ) : null}
    </div>
  );
}
