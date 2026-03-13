import { useEffect, useMemo, useState } from 'react';
import { X } from 'lucide-react';
import { HermesMark } from './HermesMark';
import { TimelineWidget } from './TimelineWidget';
import { RiskMatrixWidget } from './RiskMatrixWidget';
import { MacroSparklineWidget } from './MacroSparklineWidget';
import { PulseWidget } from './PulseWidget';

const STATUS_TIERS = [
  { level: 5, test: (s) => s.includes('CRIT'),
    shell: 'border-rose-500/30 bg-rose-950/30 text-rose-300 shadow-[0_0_20px_rgba(244,63,94,0.2)]',
    bar: 'bg-rose-400 shadow-[0_0_4px_rgba(244,63,94,0.8)]' },
  { level: 4, test: (s) => s.includes('SEVER') || s.includes('HIGH'),
    shell: 'border-orange-500/30 bg-orange-950/30 text-orange-300 shadow-[0_0_20px_rgba(249,115,22,0.18)]',
    bar: 'bg-orange-400 shadow-[0_0_4px_rgba(249,115,22,0.8)]' },
  { level: 3, test: (s) => s.includes('ELEVAT') || s.includes('VOLAT'),
    shell: 'border-amber-500/30 bg-amber-950/30 text-amber-300 shadow-[0_0_20px_rgba(245,158,11,0.16)]',
    bar: 'bg-amber-400 shadow-[0_0_4px_rgba(245,158,11,0.8)]' },
  { level: 2, test: (s) => s.includes('GUARD') || s.includes('MODER'),
    shell: 'border-blue-500/30 bg-blue-950/30 text-blue-300 shadow-[0_0_18px_rgba(59,130,246,0.14)]',
    bar: 'bg-blue-400 shadow-[0_0_4px_rgba(59,130,246,0.7)]' },
];
const STATUS_TIER_DEFAULT = {
  level: 1,
  shell: 'border-cyan-500/30 bg-cyan-950/30 text-cyan-300 shadow-[0_0_18px_rgba(34,211,238,0.14)]',
  bar: 'bg-cyan-400 shadow-[0_0_4px_rgba(34,211,238,0.7)]'
};

function getSystemStatusTone(condition) {
  const s = (condition || '').toUpperCase();
  return STATUS_TIERS.find((t) => t.test(s)) || STATUS_TIER_DEFAULT;
}

function DevelopmentModal({ dev, onClose }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const keyFacts = Array.isArray(dev.key_facts) ? dev.key_facts : [];
  const sources = Array.isArray(dev.sources) ? dev.sources : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-slate-950/75 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-2xl border border-white/10 bg-slate-900 shadow-[0_24px_60px_rgba(0,0,0,0.6)] animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-white/10 bg-slate-900/95 backdrop-blur-md px-5 py-3">
          <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-slate-400">
            <span>{dev.region || 'GLOBAL'}</span>
            <span className="text-slate-600">|</span>
            <span>{dev.domain || 'MACRO'}</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-[10px] font-mono uppercase tracking-widest text-slate-100 font-semibold bg-slate-800 px-2 py-0.5 rounded-[3px]">
              Impact: {dev.impact || 'HIGH'}
            </div>
            <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
              <X size={16} strokeWidth={2} />
            </button>
          </div>
        </div>

        <div className="px-5 py-5">
          <div className="flex gap-4 items-start mb-5">
            <div className="text-3xl mt-0.5 shrink-0">{dev.icon}</div>
            <h3 className="font-semibold text-white text-[18px] leading-snug">{dev.headline}</h3>
          </div>

          {dev.executive_summary ? (
            <p className="text-slate-300 text-[14px] leading-relaxed mb-6">{dev.executive_summary}</p>
          ) : null}

          {keyFacts.length > 0 ? (
            <>
              <h4 className="text-[10px] font-mono font-bold uppercase tracking-widest text-slate-500 mb-3">Key Facts</h4>
              <ul className="space-y-3 mb-6">
                {keyFacts.map((fact, i) => (
                  <li key={i} className="flex gap-3 text-[13px] text-slate-300 leading-relaxed">
                    <span className="text-slate-600 font-mono mt-0.5 select-none">///</span>
                    <span>{fact}</span>
                  </li>
                ))}
              </ul>
            </>
          ) : null}

          {sources.length > 0 ? (
            <>
              <h4 className="text-[10px] font-mono font-bold uppercase tracking-widest text-slate-500 mb-2">Sources</h4>
              <div className="flex flex-wrap text-[11px] font-mono text-slate-500">
                {sources.map((source, i) => {
                  const isObj = typeof source === 'object' && source !== null;
                  const url = isObj ? source.url : (typeof source === 'string' && source.startsWith('http') ? source : null);
                  const label = isObj ? source.name : source;
                  return (
                    <span key={i} className="uppercase tracking-wider">
                      {url ? (
                        <a href={url} target="_blank" rel="noopener" className="text-cyan-400 hover:text-cyan-300 underline underline-offset-2 transition-colors">{label}</a>
                      ) : (
                        label
                      )}
                      {i < sources.length - 1 && <span className="mx-2 text-slate-700 select-none">|</span>}
                    </span>
                  );
                })}
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function BriefingDisplay({ briefing }) {
  const [modalDev, setModalDev] = useState(null);
  const [consensusExpanded, setConsensusExpanded] = useState(false);
  const [contextExpanded, setContextExpanded] = useState(false);
  const systemStatus = briefing?.system_status;
  const todayIn60 = Array.isArray(briefing?.today_in_60_seconds) ? briefing.today_in_60_seconds : [];
  const developments = Array.isArray(briefing?.major_developments) ? briefing.major_developments : [];
  const consensus = Array.isArray(briefing?.analyst_consensus?.consensus)
    ? briefing.analyst_consensus.consensus
    : [];
  const friction = Array.isArray(briefing?.analyst_consensus?.friction) ? briefing.analyst_consensus.friction : [];
  const strategicContext = Array.isArray(briefing?.strategic_context) ? briefing.strategic_context : [];
  const timelineContext = briefing?.timeline_context;
  const riskMatrix = briefing?.risk_matrix;
  const macroIndicators = useMemo(() => {
    if (Array.isArray(briefing?.macro_indicators)) return briefing.macro_indicators;
    if (!Array.isArray(briefing?.macro_sparklines)) return [];

    return briefing.macro_sparklines.map((item) => ({
      id: item.id || item.label,
      title: item.title || item.label || 'Macro Trend',
      metric: item.metric || '',
      currentValue: item.currentValue || item.value || '',
      trendValue: item.trendValue || item.change || '',
      trendDirection: item.trendDirection || 'flat',
      data: Array.isArray(item.data) ? item.data : Array.isArray(item.points) ? item.points.map((point) => point.value) : [],
      details: item.details || ''
    }));
  }, [briefing?.macro_indicators, briefing?.macro_sparklines]);
  const hasSignalArchitecture =
    (Array.isArray(timelineContext?.events) && timelineContext.events.length > 0) ||
    (Array.isArray(riskMatrix?.risks) && riskMatrix.risks.length > 0) ||
    macroIndicators.length > 0;

  const systemStatusTone = getSystemStatusTone(systemStatus?.condition || systemStatus?.indicator);

  const handlePulseClick = (domain, itemId) => {
    const match = developments.find((d) => d.id === itemId)
      || developments.find((d) => (d.domain || 'MACRO') === domain);
    if (match) setModalDev(match);
  };

  if (!briefing) return null;

  return (
    <div className="pb-32 max-w-2xl mx-auto px-4">
      <header className="pt-6 pb-5 flex flex-col gap-2.5">
        <div className="flex items-center justify-center gap-3">
          <HermesMark className="h-9 w-9 shrink-0 rounded-xl shadow-[0_0_18px_rgba(34,211,238,0.16)]" />
          <h1 className="text-center text-[24px] font-extrabold uppercase tracking-[0.14em] stark-gradient-text drop-shadow-[0_0_12px_rgba(34,211,238,0.35)]">
            Hermes
          </h1>
        </div>

        <div className="flex items-center justify-between gap-2">
          <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-1.5 text-[10px] font-bold tracking-widest uppercase text-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.15)] backdrop-blur-md">
            {briefing.date?.replace(/,?\s*\d{4}$/, '')}
          </div>

          {systemStatus ? (
            <div
              className={`inline-flex items-center rounded-2xl border px-3 py-2 backdrop-blur-md ${systemStatusTone.shell}`}
            >
              <div className="flex flex-col gap-1.5 leading-none">
                <span className="text-[10px] font-mono font-bold uppercase tracking-[0.18em]">{systemStatus.condition || 'NOMINAL'}</span>
                <div className="flex items-center gap-[3px]">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div
                      key={i}
                      className={`h-[3px] w-4 rounded-full transition-all ${
                        i <= systemStatusTone.level
                          ? systemStatusTone.bar
                          : 'bg-white/10'
                      }`}
                    />
                  ))}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </header>

      <div className="space-y-8">
        <PulseWidget items={todayIn60} onItemClick={handlePulseClick} />

        {hasSignalArchitecture ? (
          <section>
            <div className="mb-4 border-l-2 border-cyan-500/40 pl-3">
              <h2 className="text-[12px] font-bold uppercase tracking-widest text-slate-300">Signal Architecture</h2>
            </div>

            <div className="grid grid-cols-1 gap-4">
              {timelineContext?.events?.length ? (
                <div>
                  <div className="text-[9px] font-mono font-bold uppercase tracking-widest text-slate-500 mb-2 pl-1">Timeline</div>
                  <TimelineWidget title={timelineContext.title || 'Timeline'} events={timelineContext.events} />
                </div>
              ) : null}
              {riskMatrix?.risks?.length ? (
                <div>
                  <div className="text-[9px] font-mono font-bold uppercase tracking-widest text-slate-500 mb-2 pl-1">Threat Map</div>
                  <RiskMatrixWidget title={riskMatrix.title || 'Threat Map'} risks={riskMatrix.risks} />
                </div>
              ) : null}
              {macroIndicators.length ? (
                <div>
                  <div className="text-[9px] font-mono font-bold uppercase tracking-widest text-slate-500 mb-2 pl-1">Quantitative</div>
                  <div className="grid grid-cols-1 gap-3">
                    {macroIndicators.slice(0, 6).map((indicator) => (
                      <MacroSparklineWidget
                        key={indicator.id || indicator.title}
                        title={indicator.title}
                        metric={indicator.metric}
                        currentValue={indicator.currentValue}
                        trendValue={indicator.trendValue}
                        trendDirection={indicator.trendDirection}
                        data={indicator.data}
                        details={indicator.details}
                      />
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </section>
        ) : null}

        {(consensus.length > 0 || friction.length > 0) ? (
          <section className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] overflow-hidden">
            <div className="px-5 pt-4 pb-3 border-b border-white/8">
              <div className="text-[10px] font-bold uppercase tracking-[0.24em] mb-1 text-purple-300">Network Consensus</div>
              <div className="grid grid-cols-2 gap-3">
                {consensus[0] ? (
                  <p className="text-[13px] text-slate-300 leading-snug line-clamp-2">
                    <span className="text-cyan-500 font-bold mr-1">›</span>{consensus[0]}
                  </p>
                ) : null}
                {friction[0] ? (
                  <p className="text-[13px] text-slate-300 leading-snug line-clamp-2">
                    <span className="text-amber-500 font-bold mr-1">›</span>{friction[0]}
                  </p>
                ) : null}
              </div>
            </div>

            {consensusExpanded ? (
              <div className="px-5 py-4 grid grid-cols-1 md:grid-cols-2 gap-3 animate-in fade-in slide-in-from-top-2 duration-200">
                <div className="bg-gradient-to-br from-cyan-950/30 to-slate-900/40 backdrop-blur-xl p-4 rounded-xl border border-cyan-500/20">
                  <h3 className="text-[10px] font-extrabold uppercase tracking-widest text-cyan-400 mb-3">Verified Patterns</h3>
                  <ul className="space-y-2.5">
                    {consensus.map((item, index) => (
                      <li key={index} className="text-[13px] text-slate-200 leading-relaxed flex gap-2">
                        <span className="text-cyan-500 font-bold shrink-0">›</span>{item}
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="bg-gradient-to-br from-amber-950/30 to-slate-900/40 backdrop-blur-xl p-4 rounded-xl border border-amber-500/20">
                  <h3 className="text-[10px] font-extrabold uppercase tracking-widest text-amber-500 mb-3">Friction Points</h3>
                  <ul className="space-y-2.5">
                    {friction.map((item, index) => (
                      <li key={index} className="text-[13px] text-slate-200 leading-relaxed flex gap-2">
                        <span className="text-amber-500 font-bold shrink-0">›</span>{item}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : null}

            {(consensus.length > 1 || friction.length > 1) ? (
              <button
                type="button"
                onClick={() => setConsensusExpanded((p) => !p)}
                className="w-full px-5 py-2.5 text-left text-[10px] font-mono uppercase tracking-widest text-slate-500 hover:text-cyan-400 transition-colors border-t border-white/5"
              >
                {consensusExpanded ? '— Show less' : `+ Show all ${Math.max(consensus.length, friction.length)} signals`}
              </button>
            ) : null}
          </section>
        ) : null}

        {strategicContext.length > 0 ? (
          <section className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] overflow-hidden">
            <div className="px-5 pt-4 pb-3 border-b border-white/8">
              <div className="text-[10px] font-bold uppercase tracking-[0.24em] mb-1 text-cyan-200">Strategic Context</div>
              <p className="text-[13.5px] text-slate-300 leading-relaxed line-clamp-2">{strategicContext[0]}</p>
            </div>

            {contextExpanded ? (
              <div className="px-5 py-4 animate-in fade-in slide-in-from-top-2 duration-200">
                {strategicContext.map((paragraph, index) => (
                  <p key={index} className="text-slate-200 leading-loose mb-4 last:mb-0 text-[14px]">
                    {paragraph}
                  </p>
                ))}
              </div>
            ) : null}

            {strategicContext.length > 1 ? (
              <button
                type="button"
                onClick={() => setContextExpanded((p) => !p)}
                className="w-full px-5 py-2.5 text-left text-[10px] font-mono uppercase tracking-widest text-slate-500 hover:text-cyan-400 transition-colors border-t border-white/5"
              >
                {contextExpanded ? '— Show less' : `+ Show ${strategicContext.length - 1} more`}
              </button>
            ) : null}
          </section>
        ) : null}

        {briefing.watchlist ? (
          <section>
            <div className="flex items-center gap-2 mb-3 border-l-2 border-amber-500/40 pl-3">
              <h2 className="text-[12px] font-bold uppercase tracking-widest text-slate-300">Watchlist</h2>
            </div>
            <div className="bg-gradient-to-r from-amber-950/40 to-transparent backdrop-blur-xl border border-amber-500/20 rounded-2xl px-5 py-4">
              <p className="text-amber-100 font-medium leading-relaxed text-[15px]">{briefing.watchlist}</p>
            </div>
          </section>
        ) : null}
      </div>

      {modalDev ? <DevelopmentModal dev={modalDev} onClose={() => setModalDev(null)} /> : null}
    </div>
  );
}
