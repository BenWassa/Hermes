import { useMemo, useRef, useState } from 'react';
import { Zap, Layers } from 'lucide-react';
import { DevelopmentCard } from './DevelopmentCard';
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

export function BriefingDisplay({ briefing }) {
  const [activeDomain, setActiveDomain] = useState('ALL');
  const tacticalRef = useRef(null);
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

  const meceDomains = useMemo(() => {
    const domains = [
      ...developments.map((dev) => dev.domain || 'MACRO'),
      ...todayIn60.map((item) => item.domain).filter(Boolean)
    ];
    const uniqueDomains = new Set(domains);
    return ['ALL', ...Array.from(uniqueDomains)];
  }, [developments, todayIn60]);

  const filteredDevelopments = useMemo(() => {
    if (activeDomain === 'ALL') return developments;
    return developments.filter((dev) => (dev.domain || 'MACRO') === activeDomain);
  }, [activeDomain, developments]);
  const systemStatusTone = getSystemStatusTone(systemStatus?.condition || systemStatus?.indicator);

  const handlePulseClick = (domain) => {
    if (domain) setActiveDomain(domain);

    if (tacticalRef.current) {
      const yOffset = -80;
      const y = tacticalRef.current.getBoundingClientRect().top + window.scrollY + yOffset;
      window.scrollTo({ top: y, behavior: 'smooth' });
    }
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
            <Zap size={14} className="animate-pulse" />
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

        <section ref={tacticalRef} className="scroll-mt-24">
          <div className="flex items-center gap-2 mb-4 pl-1">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.8)]"></div>
            <h2 className="text-[12px] font-bold uppercase tracking-widest text-slate-300">Tactical Breakdown</h2>
          </div>

          <div className="flex overflow-x-auto hide-scrollbar gap-2 mb-5 pb-2 -mx-4 px-4 md:mx-0 md:px-0">
            {meceDomains.map((domain) => {
              const isActive = activeDomain === domain;
              return (
                <button
                  key={domain}
                  onClick={() => setActiveDomain(domain)}
                  className={`whitespace-nowrap px-4 py-2 rounded-full text-[10px] font-mono font-bold uppercase tracking-widest transition-all duration-300 backdrop-blur-md flex items-center gap-2 ${
                    isActive
                      ? 'bg-cyan-950/60 border border-cyan-400/50 text-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.2)] scale-105'
                      : 'bg-white/5 border border-white/10 text-slate-400 hover:text-slate-200 hover:bg-white/10'
                  }`}
                >
                  {isActive && <Layers size={12} className="text-cyan-400" />}
                  {domain}
                </button>
              );
            })}
          </div>

          <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl px-5 py-3 shadow-[0_8px_30px_rgb(0,0,0,0.12)]">
            <div className="flex flex-col animate-in fade-in slide-in-from-bottom-2 duration-500">
              {filteredDevelopments.length > 0 ? (
                filteredDevelopments.map((development) => (
                  <DevelopmentCard key={development.id} development={development} />
                ))
              ) : (
                <div className="text-center py-8 text-slate-500 font-mono text-[11px] uppercase tracking-widest bg-white/5 border border-white/10 rounded-2xl">
                  No active signals in this sector.
                </div>
              )}
            </div>
          </div>
        </section>

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

        <DisclosurePanel title="Where the network broadly agrees, and where it doesn’t." eyebrow="Network Consensus" accentClassName="text-purple-300">
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
    </div>
  );
}
