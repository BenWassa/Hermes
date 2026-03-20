import { useState, useMemo } from 'react';
import { Copy, Check, ChevronDown, ChevronUp, ArrowRight, Zap, Layers } from 'lucide-react';
import { getDailyPrompt, getAmplifierPrompt } from '../utils/prompts';

function useCopy(timeout = 2000) {
  const [copied, setCopied] = useState(false);
  const copy = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), timeout);
    } catch {
      // fallback for iOS PWA
      const el = document.createElement('textarea');
      el.value = text;
      el.style.position = 'fixed';
      el.style.opacity = '0';
      document.body.appendChild(el);
      el.focus();
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), timeout);
    }
  };
  return [copied, copy];
}

function CopyButton({ text, label = 'Copy', copiedLabel = 'Copied', size = 'md', disabled = false }) {
  const [copied, copy] = useCopy();
  const base = size === 'lg'
    ? 'w-full flex items-center justify-center gap-2 py-4 rounded-2xl font-bold text-[12px] font-mono uppercase tracking-[0.2em] transition-all'
    : 'flex items-center gap-1.5 px-4 py-2.5 rounded-xl font-bold text-[11px] font-mono uppercase tracking-[0.18em] transition-all';
  return (
    <button
      type="button"
      onClick={() => !disabled && copy(text)}
      disabled={disabled}
      className={`${base} ${disabled
        ? 'bg-white/3 border border-white/5 text-slate-600 cursor-not-allowed'
        : copied
          ? 'bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 shadow-[0_0_16px_rgba(52,211,153,0.2)]'
          : 'bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20 hover:border-cyan-400/50 shadow-[0_0_12px_rgba(34,211,238,0.1)]'
      }`}
    >
      {copied
        ? <><Check size={size === 'lg' ? 16 : 14} strokeWidth={2.5} />{copiedLabel}</>
        : <><Copy size={size === 'lg' ? 16 : 14} strokeWidth={2} />{label}</>
      }
    </button>
  );
}

function StepBadge({ n }) {
  return (
    <span className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-mono font-bold bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 shrink-0">
      {n}
    </span>
  );
}

function SectionCard({ children, className = '' }) {
  return (
    <div className={`bg-white/5 border border-white/10 rounded-2xl p-5 backdrop-blur-xl shadow-[0_12px_40px_rgba(0,0,0,0.2)] ${className}`}>
      {children}
    </div>
  );
}

function DailySection({ onGoToImport }) {
  const today = new Date();
  const dateStr = today.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  const prompt = useMemo(() => getDailyPrompt(dateStr), [dateStr]);
  const [showPrompt, setShowPrompt] = useState(false);

  return (
    <SectionCard>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center bg-cyan-950/60 border border-cyan-500/20 text-cyan-300 shrink-0">
          <Zap size={16} strokeWidth={2} />
        </div>
        <div>
          <h2 className="text-[12px] font-bold font-mono uppercase tracking-[0.22em] text-slate-100">Daily Briefing</h2>
          <p className="text-[10px] font-mono text-slate-500 uppercase tracking-[0.16em] mt-0.5">{dateStr}</p>
        </div>
      </div>

      <ol className="space-y-3 mb-5">
        <li className="flex items-start gap-3 text-[12px] text-slate-300">
          <StepBadge n="1" />
          <span>Copy the prompt below and paste it into ChatGPT</span>
        </li>
        <li className="flex items-start gap-3 text-[12px] text-slate-300">
          <StepBadge n="2" />
          <span>Copy the JSON response ChatGPT returns</span>
        </li>
        <li className="flex items-start gap-3 text-[12px] text-slate-300">
          <StepBadge n="3" />
          <span>Come back here and tap <strong className="text-cyan-300">Import Result</strong></span>
        </li>
      </ol>

      <CopyButton text={prompt} label="Copy Daily Prompt" copiedLabel="Prompt Copied!" size="lg" />

      <button
        type="button"
        onClick={onGoToImport}
        className="mt-3 w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl border border-white/10 bg-white/5 text-slate-300 hover:text-slate-100 hover:bg-white/10 font-bold text-[11px] font-mono uppercase tracking-[0.18em] transition-all"
      >
        Import Result <ArrowRight size={14} strokeWidth={2} />
      </button>

      <button
        type="button"
        onClick={() => setShowPrompt((s) => !s)}
        className="mt-3 w-full flex items-center justify-center gap-1.5 text-[10px] font-mono text-slate-600 hover:text-slate-400 uppercase tracking-[0.16em] transition-colors"
      >
        {showPrompt ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        {showPrompt ? 'Hide' : 'Preview'} prompt text
      </button>

      {showPrompt && (
        <pre className="mt-3 text-[10px] text-slate-400 font-mono leading-relaxed whitespace-pre-wrap break-words bg-slate-950/60 border border-white/5 rounded-xl p-4 max-h-64 overflow-y-auto">
          {prompt}
        </pre>
      )}
    </SectionCard>
  );
}

function AmplifierSection({ todaysBriefing, onGoToImport }) {
  const prompt = useMemo(() => {
    if (!todaysBriefing) return null;
    return getAmplifierPrompt(todaysBriefing);
  }, [todaysBriefing]);

  const hasToday = Boolean(todaysBriefing);

  return (
    <SectionCard>
      <div className="flex items-center gap-3 mb-4">
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 border ${hasToday ? 'bg-cyan-950/60 border-cyan-500/20 text-cyan-300' : 'bg-slate-900/60 border-white/8 text-slate-600'}`}>
          <Layers size={16} strokeWidth={2} />
        </div>
        <div>
          <h2 className="text-[12px] font-bold font-mono uppercase tracking-[0.22em] text-slate-100">
            Intelligence Amplifier
          </h2>
          <p className="text-[10px] font-mono text-slate-500 uppercase tracking-[0.16em] mt-0.5">
            {hasToday ? 'Today\'s briefing ready — run Step 2' : 'Import today\'s briefing first'}
          </p>
        </div>
      </div>

      <ol className="space-y-3 mb-5">
        <li className="flex items-start gap-3 text-[12px] text-slate-300">
          <StepBadge n="1" />
          <span>Copy the prompt below — your briefing from Step 1 is embedded inside</span>
        </li>
        <li className="flex items-start gap-3 text-[12px] text-slate-300">
          <StepBadge n="2" />
          <span>Paste into ChatGPT and copy the Intelligence Amplifier JSON response</span>
        </li>
        <li className="flex items-start gap-3 text-[12px] text-slate-300">
          <StepBadge n="3" />
          <span>Return here and tap <strong className="text-cyan-300">Import Result</strong></span>
        </li>
      </ol>

      <CopyButton
        text={prompt || ''}
        label="Copy Amplifier Prompt"
        copiedLabel="Prompt + Briefing Copied!"
        size="lg"
        disabled={!hasToday}
      />

      <button
        type="button"
        onClick={onGoToImport}
        disabled={!hasToday}
        className={`mt-3 w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl border font-bold text-[11px] font-mono uppercase tracking-[0.18em] transition-all ${hasToday ? 'border-white/10 bg-white/5 text-slate-300 hover:text-slate-100 hover:bg-white/10' : 'border-white/5 bg-white/3 text-slate-600 cursor-not-allowed'}`}
      >
        Import Result <ArrowRight size={14} strokeWidth={2} />
      </button>

      {!hasToday ? (
        <p className="mt-3 text-center text-[10px] font-mono text-slate-600 uppercase tracking-[0.16em]">
          Complete Step 1 to unlock
        </p>
      ) : null}
    </SectionCard>
  );
}

export function WorkflowView({ todaysBriefing, onGoToImport }) {
  return (
    <div className="pb-32 max-w-2xl mx-auto pt-8 px-4 animate-in fade-in duration-300">
      <header className="pb-6 flex flex-col items-center text-center">
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center bg-cyan-950/40 border border-cyan-500/20 text-cyan-300 shadow-[0_0_20px_rgba(34,211,238,0.12)] backdrop-blur-md mb-4">
          <Zap size={24} strokeWidth={2} />
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight stark-gradient-text uppercase drop-shadow-[0_0_15px_rgba(34,211,238,0.35)] mb-2">
          Workflow
        </h1>
        <p className="text-[11px] font-bold text-slate-400 uppercase tracking-[0.28em] font-mono">
          Intelligence Collection Protocol
        </p>
      </header>

      <div className="space-y-4">
        <DailySection onGoToImport={onGoToImport} />
        <AmplifierSection todaysBriefing={todaysBriefing} onGoToImport={onGoToImport} />
      </div>
    </div>
  );
}
