import { Activity } from 'lucide-react';

function buildPath(points, width, height, padding) {
  if (!Array.isArray(points) || points.length === 0) return '';

  const numeric = points.map((point) => Number(point.value)).filter((value) => Number.isFinite(value));
  if (numeric.length === 0) return '';

  const min = Math.min(...numeric);
  const max = Math.max(...numeric);
  const range = max - min || 1;

  return numeric
    .map((value, index) => {
      const x = padding + (index * (width - padding * 2)) / Math.max(numeric.length - 1, 1);
      const y = height - padding - ((value - min) / range) * (height - padding * 2);
      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
    })
    .join(' ');
}

function getLastPointMeta(points, width, height, padding) {
  if (!Array.isArray(points) || points.length === 0) return null;

  const numeric = points.map((point) => Number(point.value)).filter((value) => Number.isFinite(value));
  if (numeric.length === 0) return null;

  const min = Math.min(...numeric);
  const max = Math.max(...numeric);
  const range = max - min || 1;
  const value = numeric[numeric.length - 1];
  const x = padding + ((numeric.length - 1) * (width - padding * 2)) / Math.max(numeric.length - 1, 1);
  const y = height - padding - ((value - min) / range) * (height - padding * 2);

  return { x, y };
}

export function SparklineWidget({ items }) {
  const safeItems = Array.isArray(items) ? items.slice(0, 3) : [];

  if (safeItems.length === 0) return null;

  return (
    <div className="grid grid-cols-1 gap-3">
      {safeItems.map((item) => {
        const path = buildPath(item.points, 160, 54, 6);
        const latestPoint = getLastPointMeta(item.points, 160, 54, 6);

        return (
          <div
            key={item.label}
            className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl px-4 py-3 shadow-[0_8px_30px_rgb(0,0,0,0.12)]"
          >
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <Activity size={14} className="text-cyan-400" />
                  <h3 className="text-[11px] font-bold uppercase tracking-[0.2em] text-cyan-300">{item.label}</h3>
                </div>
                <div className="text-[13px] font-semibold text-white">{item.value}</div>
                {item.change ? <div className="text-[11px] text-slate-400 mt-0.5">{item.change}</div> : null}
              </div>

              <div className="shrink-0">
                <svg width="160" height="54" viewBox="0 0 160 54" className="overflow-visible">
                  <path d="M 6 48 L 154 48" stroke="rgba(148,163,184,0.18)" strokeWidth="1" />
                  {path ? (
                    <path
                      d={path}
                      fill="none"
                      stroke="rgba(34,211,238,0.95)"
                      strokeWidth="2.25"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  ) : null}
                  {latestPoint ? (
                    <circle
                      cx={latestPoint.x}
                      cy={latestPoint.y}
                      r="3"
                      fill="rgba(34,211,238,1)"
                      stroke="rgba(8,15,27,0.95)"
                      strokeWidth="1.5"
                    />
                  ) : null}
                </svg>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
