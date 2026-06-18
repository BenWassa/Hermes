import { Zap, Layers, Clipboard, AlertTriangle, ArrowRight } from 'lucide-react';

export function ImportFlowView({ step, isLoading, error, isImporting, onClipboardPaste, onGoToWorkflow }) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[75vh] gap-8 animate-in fade-in duration-500 px-4">
        <div className="w-16 h-16 rounded-2xl flex items-center justify-center bg-cyan-950/40 border border-cyan-500/20 text-cyan-400 shadow-[0_0_20px_rgba(34,211,238,0.12)] backdrop-blur-md">
          <Zap size={28} strokeWidth={1.8} className="animate-pulse" />
        </div>
        <div className="text-center space-y-2">
          <p className="text-[11px] font-mono font-bold uppercase tracking-[0.28em] text-cyan-400/70">
            Syncing Intelligence Layer
          </p>
          <p className="text-[10px] font-mono text-slate-500 uppercase tracking-[0.18em]">
            Initialising briefing...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[75vh] px-4 max-w-sm mx-auto animate-in fade-in duration-500">
      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-8">
        <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-mono font-bold border transition-colors ${
          step === 1
            ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-300'
            : 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
        }`}>
          {step === 1 ? '1' : '✓'}
        </div>
        <div className="h-px w-8 bg-white/10" />
        <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-mono font-bold border transition-colors ${
          step === 2
            ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-300'
            : 'bg-white/5 border-white/10 text-slate-600'
        }`}>
          2
        </div>
      </div>

      {/* Icon */}
      <div className="w-14 h-14 rounded-2xl flex items-center justify-center bg-cyan-950/40 border border-cyan-500/20 text-cyan-400 shadow-[0_0_20px_rgba(34,211,238,0.12)] backdrop-blur-md mb-5">
        {step === 1 ? <Zap size={24} strokeWidth={2} /> : <Layers size={24} strokeWidth={2} />}
      </div>

      <h2 className="text-2xl font-extrabold stark-gradient-text tracking-tight uppercase mb-2 drop-shadow-[0_0_15px_rgba(34,211,238,0.35)]">
        {step === 1 ? 'Daily Briefing' : 'Intel Amplifier'}
      </h2>
      <p className="text-[11px] font-mono text-slate-500 uppercase tracking-[0.22em] mb-8 text-center">
        {step === 1 ? 'Step 1 of 2 — Paste briefing JSON' : 'Step 2 of 2 — Paste amplifier JSON'}
      </p>

      <p className="text-[13px] text-slate-400 leading-relaxed text-center mb-8">
        {step === 1
          ? 'Your ChatGPT daily task has run. Copy the JSON output and tap below.'
          : 'Open your ChatGPT Amplifier chat, paste the briefing JSON, copy the output, then tap below.'}
      </p>

      {error ? (
        <div className="w-full mb-5 bg-red-950/20 text-red-300 p-4 border border-red-500/20 rounded-2xl flex items-start gap-3">
          <AlertTriangle size={16} className="mt-0.5 shrink-0 text-red-400" />
          <div className="text-[12px] font-mono leading-relaxed">{error}</div>
        </div>
      ) : null}

      <button
        type="button"
        onClick={onClipboardPaste}
        disabled={isImporting}
        className="w-full flex items-center justify-center gap-2.5 bg-cyan-500 text-slate-950 font-bold py-4 px-6 rounded-full shadow-[0_0_24px_rgba(34,211,238,0.28)] active:scale-[0.98] transition-all uppercase tracking-[0.2em] text-[13px] hover:bg-cyan-400 disabled:opacity-60 disabled:cursor-not-allowed"
      >
        <Clipboard size={18} strokeWidth={2.5} />
        {isImporting ? 'Importing...' : 'Paste from Clipboard'}
      </button>

      {step === 1 ? (
        <button
          type="button"
          onClick={onGoToWorkflow}
          className="mt-5 flex items-center gap-1.5 text-[10px] font-mono text-slate-600 hover:text-slate-400 uppercase tracking-[0.18em] transition-colors"
        >
          Run workflow manually <ArrowRight size={10} />
        </button>
      ) : null}
    </div>
  );
}
