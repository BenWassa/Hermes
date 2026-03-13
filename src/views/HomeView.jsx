import { Plus, ArrowRight, Terminal } from 'lucide-react';
import { BriefingDisplay } from '../components/BriefingDisplay';

export function HomeView({ activeBriefing, latestBriefing, onGoAdd, onOpenBriefing, onOpenMenu }) {
  if (activeBriefing) {
    return <BriefingDisplay briefing={activeBriefing} onOpenMenu={onOpenMenu} />;
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[75vh] px-4 max-w-sm mx-auto text-center space-y-8 animate-in fade-in duration-500">
      <div className="flex flex-col items-center">
        <div className="w-16 h-16 rounded-2xl flex items-center justify-center bg-cyan-950/40 border border-cyan-500/20 text-cyan-400 shadow-[0_0_20px_rgba(34,211,238,0.12)] backdrop-blur-md mb-6">
          <Terminal size={30} strokeWidth={1.6} />
        </div>
        <h2 className="text-3xl font-extrabold stark-gradient-text tracking-tight uppercase mb-3 drop-shadow-[0_0_15px_rgba(34,211,238,0.35)]">
          Awaiting Input
        </h2>
        <p className="text-[14px] text-slate-400 leading-relaxed font-medium">
          Your intelligence panel is currently empty for today. Paste your generated JSON to populate the dashboard.
        </p>
      </div>

      <div className="w-full space-y-4">
        <button
          onClick={onGoAdd}
          className="w-full flex items-center justify-center gap-2 bg-cyan-500 text-slate-950 font-bold py-4 px-6 rounded-full shadow-[0_0_24px_rgba(34,211,238,0.24)] active:scale-[0.98] transition-all uppercase tracking-[0.2em] text-[13px] hover:bg-cyan-400"
        >
          <Plus size={18} strokeWidth={2.5} />
          Add Today's Briefing
        </button>

        {latestBriefing && (
          <button
            onClick={() => onOpenBriefing(latestBriefing.id)}
            className="w-full flex items-center justify-center gap-2 bg-white/5 border border-white/10 text-slate-200 font-bold py-3.5 px-6 rounded-full hover:bg-white/10 active:scale-[0.98] transition-all uppercase tracking-[0.2em] text-[11px] backdrop-blur-xl"
          >
            Load Previous: {latestBriefing.date}
            <ArrowRight size={14} strokeWidth={2} />
          </button>
        )}
      </div>
    </div>
  );
}
