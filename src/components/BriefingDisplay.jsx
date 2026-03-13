import { useEffect, useMemo, useState } from 'react';
import { X } from 'lucide-react';
import { DisclosurePanel } from './DisclosurePanel';
import { TimelineWidget } from './TimelineWidget';
import { RiskMatrixWidget } from './RiskMatrixWidget';
import { MacroSparklineWidget } from './MacroSparklineWidget';
import { PulseWidget } from './PulseWidget';

function getSystemStatusTone(condition) {
  const normalized = (condition || '').toUpperCase();

  if (normalized.includes('CRIT')) {
    return {
      shell: 'border-rose-500/30 bg-rose-950/30 text-rose-300 shadow-[0_0_20px_rgba(244,63,94,0.18)]',
      dot: 'bg-rose-400 shadow-[0_0_10px_rgba(244,63,94,0.9)] animate-pulse'
    };
  }
  if (normalized.includes('ELEVAT') || normalized.includes('VOLAT')) {
    return {
      shell: 'border-amber-500/30 bg-amber-950/30 text-amber-300 shadow-[0_0_20px_rgba(245,158,11,0.16)]',
      dot: 'bg-amber-400 shadow-[0_0_10px_rgba(245,158,11,0.85)] animate-pulse'
    };
  }
  return {
    shell: 'border-cyan-500/30 bg-cyan-950/30 text-cyan-300 shadow-[0_0_18px_rgba(34,211,238,0.14)]',
    dot: 'bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.8)]'
  };
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
                {sources.map((source, i) => (
                  <span key={i} className="uppercase tracking-wider">
                    {source}
                    {i < sources.length - 1 && <span className="mx-2 text-slate-700 select-none">|</span>}
                  </span>
                ))}
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
      <header className="pt-8 pb-6 flex flex-col gap-3">
        <h1 className="text-center text-[30px] font-extrabold uppercase tracking-tight stark-gradient-text drop-shadow-[0_0_15px_rgba(34,211,238,0.4)] sm:text-[34px]">
          GlobalBrief
        </h1>

        <div className="flex items-center justify-between gap-2">
          <div className="inline-flex min-h-9 items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/40 px-4 py-1.5 text-[11px] font-bold tracking-widest uppercase text-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.15)] backdrop-blur-md">
            {briefing.date?.replace(/,?\s*\d{4}$/, '')}
          </div>

          {systemStatus ? (
            <div
              className={`inline-flex min-h-9 items-center gap-2 rounded-full border px-3.5 py-1.5 text-[10px] font-mono font-bold uppercase tracking-[0.22em] backdrop-blur-md ${systemStatusTone.shell}`}
            >
              <div className={`h-2 w-2 rounded-full ${systemStatusTone.dot}`}></div>
              <span>{systemStatus.condition || 'Nominal'}</span>
              {systemStatus.indicator ? <span className="text-white/35">/</span> : null}
              {systemStatus.indicator ? <span>{systemStatus.indicator}</span> : null}
            </div>
          ) : null}
        </div>
      </header>

      <div className="space-y-8">
        <PulseWidget items={todayIn60} onItemClick={handlePulseClick} />

        {hasSignalArchitecture ? (
          <section>
            <div className="flex items-center gap-2 mb-4 pl-1">
              <div className="w-1.5 h-1.5 rounded-full bg-cyan-300 shadow-[0_0_8px_rgba(165,243,252,0.8)]"></div>
              <h2 className="text-[12px] font-bold uppercase tracking-widest text-slate-300">Signal Architecture</h2>
            </div>

            <DisclosurePanel
              title="Visual streams for chronology, risk concentration, and trend direction."
              eyebrow="Scan Layer"
              accentClassName="text-cyan-400"
              defaultOpen
            >
              <div className="grid grid-cols-1 gap-4">
                {timelineContext?.events?.length ? (
                  <TimelineWidget title={timelineContext.title || 'Escalation Timeline'} events={timelineContext.events} />
                ) : null}
                {riskMatrix?.risks?.length ? (
                  <RiskMatrixWidget title={riskMatrix.title || 'Risk Matrix'} risks={riskMatrix.risks} />
                ) : null}
                {macroIndicators.length ? (
                  <div className="grid grid-cols-1 gap-3">
                    {macroIndicators.slice(0, 3).map((indicator) => (
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
                ) : null}
              </div>
            </DisclosurePanel>
          </section>
        ) : null}

        <DisclosurePanel title="Where the network broadly agrees, and where it doesn't." eyebrow="Network Consensus" accentClassName="text-purple-300">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
            <div className="bg-gradient-to-br from-cyan-950/30 to-slate-900/40 backdrop-blur-xl p-5 rounded-2xl border border-cyan-500/20 shadow-[0_0_20px_rgba(34,211,238,0.05)]">
              <h3 className="text-[11px] font-extrabold uppercase tracking-widest text-cyan-400 mb-4">Verified Patterns</h3>
              <ul className="space-y-3">
                {consensus.map((item, index) => (
                  <li key={index} className="text-[13.5px] text-slate-200 leading-relaxed flex gap-2">
                    <span className="text-cyan-500 font-bold">›</span> {item}
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-gradient-to-br from-amber-950/30 to-slate-900/40 backdrop-blur-xl p-5 rounded-2xl border border-amber-500/20 shadow-[0_0_20px_rgba(245,158,11,0.05)]">
              <h3 className="text-[11px] font-extrabold uppercase tracking-widest text-amber-500 mb-4">Friction Points</h3>
              <ul className="space-y-3">
                {friction.map((item, index) => (
                  <li key={index} className="text-[13.5px] text-slate-200 leading-relaxed flex gap-2">
                    <span className="text-amber-500 font-bold">›</span> {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </DisclosurePanel>

        <DisclosurePanel title="Longer-form strategic framing behind the daily signals." eyebrow="Strategic Context" accentClassName="text-cyan-200">
          <div className="pt-1">
            {strategicContext.map((paragraph, index) => (
              <p key={index} className="text-slate-200 leading-loose mb-4 last:mb-0 text-[14.5px]">
                {paragraph}
              </p>
            ))}
          </div>
        </DisclosurePanel>

        <DisclosurePanel title="Forward-looking analyst note for the next 24 to 72 hours." eyebrow="Watchlist" accentClassName="text-amber-300">
          <div className="bg-gradient-to-r from-amber-950/40 to-transparent backdrop-blur-xl border border-amber-500/20 rounded-2xl px-5 py-4 mt-1">
            <p className="text-amber-100 font-medium leading-relaxed text-[15px]">{briefing.watchlist}</p>
          </div>
        </DisclosurePanel>
      </div>

      {modalDev ? <DevelopmentModal dev={modalDev} onClose={() => setModalDev(null)} /> : null}
    </div>
  );
}
