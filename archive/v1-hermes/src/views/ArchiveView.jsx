import { useState, useMemo } from 'react';
import { ArrowUpRight, FolderArchive, Plus, Trash2 } from 'lucide-react';

const CHANGE_TYPE_COLORS = {
  escalating:  'text-rose-300 border-rose-500/30 bg-rose-950/30',
  new:         'text-cyan-300 border-cyan-500/30 bg-cyan-950/30',
  stabilizing: 'text-emerald-300 border-emerald-500/30 bg-emerald-950/30',
  resolving:   'text-blue-300 border-blue-500/30 bg-blue-950/30',
  unchanged:   'text-slate-400 border-slate-500/20 bg-slate-800/20',
};

function changeTypeColor(ct) {
  return CHANGE_TYPE_COLORS[(ct || '').toLowerCase()] || CHANGE_TYPE_COLORS.unchanged;
}

function DateView({ briefings, onOpenBriefing, onDeleteBriefing, canDelete }) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl px-5 backdrop-blur-xl shadow-[0_12px_40px_rgba(0,0,0,0.2)]">
      {briefings.map((briefing) => (
        <div
          key={briefing.id}
          className="flex items-center justify-between py-4 border-b border-white/10 last:border-b-0"
        >
          <button
            type="button"
            onClick={() => onOpenBriefing(briefing.id)}
            className="group flex min-w-0 flex-1 items-center justify-between text-left transition-colors hover:bg-white/5"
          >
            <div className="min-w-0 flex-1 pr-4">
              <div className="mb-1.5 flex min-w-0 flex-wrap items-center gap-2 sm:gap-3">
                <span className="min-w-0 break-words text-[12px] font-bold font-mono text-slate-100 uppercase tracking-[0.2em]">
                  {briefing.date}
                </span>
                <span className="max-w-full truncate text-[9px] font-mono text-cyan-400 uppercase tracking-[0.22em] bg-cyan-950/40 border border-cyan-500/20 px-2 py-1 rounded-sm shadow-[0_0_10px_rgba(34,211,238,0.1)]">
                  ID: {briefing.id.slice(0, 8)}
                </span>
              </div>

              <div className="min-w-0 flex items-center gap-2 text-[13px] text-slate-400">
                <span className="shrink-0 text-[10px] font-mono text-cyan-400 drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]">///</span>
                <span className="min-w-0 truncate font-medium">
                  {[briefing.today_in_60_seconds?.[0]?.headline, briefing.today_in_60_seconds?.[1]?.headline]
                    .filter(Boolean)
                    .join(' | ') || 'No pulse preview available.'}
                </span>
              </div>
            </div>
            <div className="ml-3 shrink-0 text-slate-500 transition-colors group-hover:text-cyan-300">
              <ArrowUpRight size={20} strokeWidth={1.5} />
            </div>
          </button>

          {canDelete ? (
            <button
              type="button"
              aria-label={`Delete briefing ${briefing.date || briefing.id}`}
              onClick={() => onDeleteBriefing?.(briefing)}
              className="ml-3 shrink-0 rounded-xl border border-red-500/20 bg-red-950/20 p-2 text-red-300 transition-colors hover:border-red-400/40 hover:bg-red-950/30 hover:text-red-200"
            >
              <Trash2 size={15} strokeWidth={1.8} />
            </button>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function ThreadView({ briefings, onOpenThread }) {
  const storyMap = useMemo(() => {
    const map = {};
    briefings.forEach((briefing) => {
      const devs = Array.isArray(briefing.major_developments) ? briefing.major_developments : [];
      devs.forEach((dev) => {
        if (!dev.story_id) return;
        if (!map[dev.story_id]) {
          map[dev.story_id] = { storyId: dev.story_id, appearances: [], latestHeadline: dev.headline, latestChangeType: dev.change_type };
        }
        map[dev.story_id].appearances.push({ briefingId: briefing.id, briefingDate: briefing.date, changeType: dev.change_type });
        map[dev.story_id].latestHeadline = dev.headline;
        map[dev.story_id].latestChangeType = dev.change_type;
      });
    });
    return Object.values(map).sort((a, b) => {
      const latestA = a.appearances[0]?.briefingId || '';
      const latestB = b.appearances[0]?.briefingId || '';
      return latestB.localeCompare(latestA);
    });
  }, [briefings]);

  const untaggedCount = briefings.reduce((acc, b) => {
    const devs = Array.isArray(b.major_developments) ? b.major_developments : [];
    return acc + devs.filter((d) => !d.story_id).length;
  }, 0);

  if (storyMap.length === 0) {
    return (
      <div className="text-[11px] text-slate-400 py-8 border border-white/10 bg-white/5 rounded-2xl px-5 backdrop-blur-xl font-mono uppercase tracking-[0.2em] text-center">
        STATUS: No story_id fields found in archive. Import briefings with the new schema to enable thread view.
        {untaggedCount > 0 ? ` (${untaggedCount} untagged development${untaggedCount !== 1 ? 's' : ''} found)` : ''}
      </div>
    );
  }

  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl px-5 backdrop-blur-xl shadow-[0_12px_40px_rgba(0,0,0,0.2)]">
      {storyMap.map(({ storyId, appearances, latestHeadline, latestChangeType }) => (
        <button
          key={storyId}
          onClick={() => onOpenThread(storyId)}
          className="w-full flex items-start justify-between py-4 border-b border-white/10 last:border-b-0 hover:bg-white/5 transition-colors text-left group"
        >
          <div className="min-w-0 flex-1 pr-4">
            <div className="mb-1.5 flex items-center gap-2 flex-wrap">
              <span className="text-[13px] font-semibold text-slate-100 leading-snug">{latestHeadline || storyId}</span>
              {latestChangeType ? (
                <span className={`text-[8px] font-mono font-bold uppercase tracking-[0.2em] px-1.5 py-0.5 rounded border ${changeTypeColor(latestChangeType)}`}>
                  {latestChangeType}
                </span>
              ) : null}
            </div>
            <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500 uppercase tracking-[0.16em]">
              <span className="text-cyan-400/60 font-bold select-none">///</span>
              <span>{storyId}</span>
              <span className="text-slate-600">{appearances.length} briefing{appearances.length !== 1 ? 's' : ''}</span>
              <span className="text-slate-700">{appearances[appearances.length - 1]?.briefingId} → {appearances[0]?.briefingId}</span>
            </div>
          </div>
          <div className="ml-3 shrink-0 text-slate-500 group-hover:text-cyan-300 transition-colors mt-0.5">
            <ArrowUpRight size={20} strokeWidth={1.5} />
          </div>
        </button>
      ))}
    </div>
  );
}

export function ArchiveView({
  briefings,
  onOpenBriefing,
  onOpenThread,
  onAdd,
  onDeleteBriefing,
  canImport,
  canDelete
}) {
  const [mode, setMode] = useState('date');

  return (
    <div className="pb-32 max-w-2xl mx-auto pt-8 px-4 animate-in fade-in duration-300 relative min-h-app-offset-8">
      <header className="pb-6 flex flex-col items-center text-center">
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center bg-blue-950/40 border border-blue-500/20 text-blue-300 shadow-[0_0_20px_rgba(96,165,250,0.12)] backdrop-blur-md mb-4">
          <FolderArchive size={24} strokeWidth={2} />
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight stark-gradient-text uppercase drop-shadow-[0_0_15px_rgba(34,211,238,0.35)] mb-2">
          Intelligence Archive
        </h1>
        <p className="text-[11px] font-bold text-slate-400 uppercase tracking-[0.28em] font-mono">
          Historical Database Records: {briefings.length}
        </p>
      </header>

      {briefings.length > 0 ? (
        <div className="flex items-center gap-1 mb-5 bg-white/5 border border-white/10 rounded-full p-1 w-fit mx-auto backdrop-blur-xl">
          <button
            type="button"
            onClick={() => setMode('date')}
            className={`px-4 py-1.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-[0.2em] transition-all ${
              mode === 'date'
                ? 'bg-cyan-500 text-slate-950 shadow-[0_0_12px_rgba(34,211,238,0.3)]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            By Date
          </button>
          <button
            type="button"
            onClick={() => setMode('thread')}
            className={`px-4 py-1.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-[0.2em] transition-all ${
              mode === 'thread'
                ? 'bg-cyan-500 text-slate-950 shadow-[0_0_12px_rgba(34,211,238,0.3)]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            By Thread
          </button>
        </div>
      ) : null}

      {briefings.length === 0 ? (
        <div className="text-[11px] text-slate-400 py-8 border border-white/10 bg-white/5 rounded-2xl px-5 backdrop-blur-xl font-mono uppercase tracking-[0.2em] text-center">
          STATUS: No shared historical records available.
        </div>
      ) : mode === 'date' ? (
        <DateView
          briefings={briefings}
          onOpenBriefing={onOpenBriefing}
          onDeleteBriefing={onDeleteBriefing}
          canDelete={canDelete}
        />
      ) : (
        <ThreadView briefings={briefings} onOpenThread={onOpenThread} />
      )}

      {canImport ? (
        <div
          className="fixed left-0 w-full z-40 pointer-events-none flex justify-center px-6"
          style={{ bottom: 'max(8.25rem, calc(env(safe-area-inset-bottom) + 6.75rem))' }}
        >
          <div className="w-full max-w-2xl flex justify-end">
            <button
              onClick={onAdd}
              className="pointer-events-auto flex items-center gap-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 px-5 py-3.5 rounded-full font-bold uppercase tracking-wider text-xs font-mono shadow-[0_12px_30px_rgba(0,0,0,0.35),_0_0_25px_rgba(34,211,238,0.35)] hover:shadow-[0_16px_36px_rgba(0,0,0,0.4),_0_0_35px_rgba(34,211,238,0.5)] transition-all transform hover:scale-105"
            >
              <Plus size={18} strokeWidth={2.5} />
              Import Briefing
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
