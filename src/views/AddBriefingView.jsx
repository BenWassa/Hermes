import { useEffect, useState } from 'react';
import { Database, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import { DisclosurePanel } from '../components/DisclosurePanel';
import { sanitizeJsonInput } from '../utils/json';

const SCHEMA_REFERENCE = `{
  "id": "2026-03-13",
  "date": "March 13, 2026",
  "today_in_60_seconds": [
    {
      "icon": "🛢️",
      "headline": "Oil volatility spikes",
      "domain": "ENERGY"
    }
  ]
}`;

export function AddBriefingView({ jsonInput, error: submitError, onJsonChange, onImport, onLoadSample }) {
  const [liveStatus, setLiveStatus] = useState({ type: '', message: '' });

  useEffect(() => {
    const timer = setTimeout(() => {
      if (!jsonInput.trim()) {
        setLiveStatus({ type: '', message: '' });
        return;
      }

      try {
        const parsed = JSON.parse(sanitizeJsonInput(jsonInput));
        const missing = [];

        if (!parsed.id) missing.push('id');
        if (!parsed.date) missing.push('date');
        if (!parsed.today_in_60_seconds || !Array.isArray(parsed.today_in_60_seconds)) {
          missing.push('today_in_60_seconds (must be array)');
        }

        if (missing.length > 0) {
          setLiveStatus({
            type: 'warning',
            message: `Valid JSON, but missing required fields: ${missing.join(', ')}`
          });
          return;
        }

        setLiveStatus({
          type: 'success',
          message: 'Schema valid and ready for import.'
        });
      } catch {
        setLiveStatus({
          type: 'error',
          message: 'Invalid JSON syntax - check for missing commas or unclosed brackets.'
        });
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [jsonInput]);

  return (
    <div className="pb-24 max-w-2xl mx-auto pt-8 px-4 animate-in fade-in duration-300">
      <header className="pb-6 flex flex-col items-center text-center">
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center bg-cyan-950/40 border border-cyan-500/20 text-cyan-400 shadow-[0_0_20px_rgba(34,211,238,0.12)] backdrop-blur-md mb-4">
          <Database size={24} strokeWidth={2} />
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight stark-gradient-text uppercase drop-shadow-[0_0_15px_rgba(34,211,238,0.35)] mb-2">
          Import Intelligence
        </h1>
        <p className="text-[11px] font-bold text-slate-400 uppercase tracking-[0.28em]">
          Secure JSON Ingestion Protocol
        </p>
      </header>

      {submitError && (
        <div className="bg-red-950/20 text-red-300 p-4 mb-6 border border-red-500/20 rounded-2xl flex items-start gap-3 backdrop-blur-md shadow-[0_0_20px_rgba(239,68,68,0.08)]">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-red-400" />
          <div className="text-[12px] font-medium leading-relaxed">{submitError}</div>
        </div>
      )}

      {!submitError && liveStatus.message ? (
        <div
          className={`mb-6 flex items-start gap-3 rounded-2xl border p-4 backdrop-blur-md transition-colors ${
            liveStatus.type === 'success'
              ? 'border-emerald-500/20 bg-emerald-950/20 text-emerald-300 shadow-[0_0_20px_rgba(16,185,129,0.08)]'
              : liveStatus.type === 'warning'
                ? 'border-amber-500/20 bg-amber-950/20 text-amber-300 shadow-[0_0_20px_rgba(245,158,11,0.08)]'
                : 'border-slate-500/20 bg-slate-900/40 text-slate-400'
          }`}
        >
          {liveStatus.type === 'success' ? (
            <CheckCircle size={18} className="mt-0.5 shrink-0 text-emerald-400" />
          ) : liveStatus.type === 'warning' ? (
            <Info size={18} className="mt-0.5 shrink-0 text-amber-400" />
          ) : (
            <AlertTriangle size={18} className="mt-0.5 shrink-0 text-slate-500" />
          )}
          <div className="text-[12px] font-mono font-medium leading-relaxed">{liveStatus.message}</div>
        </div>
      ) : null}

      <div className="relative group mb-6">
        <div className="absolute top-0 left-0 w-full h-9 bg-white/10 rounded-t-2xl flex items-center px-4 border border-b-0 border-white/10 backdrop-blur-xl">
          <span className="text-[10px] font-mono font-bold uppercase tracking-[0.24em] text-slate-400">
            data.json
          </span>
        </div>
        <textarea
          value={jsonInput}
          onChange={(event) => onJsonChange(event.target.value)}
          placeholder="Paste generated JSON schema here..."
          className="w-full h-[400px] mt-9 bg-white/5 border border-white/10 rounded-b-2xl p-4 font-mono text-[13px] text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/40 resize-none transition-colors backdrop-blur-xl shadow-[0_12px_40px_rgba(0,0,0,0.2)]"
          spellCheck={false}
        />
      </div>

      <DisclosurePanel
        title="Expected JSON Structure"
        eyebrow="Format Reference"
        accentClassName="text-slate-400"
      >
        <pre className="overflow-x-auto rounded-xl border border-white/5 bg-slate-950/50 p-4 font-mono text-[11px] text-slate-300">
          {SCHEMA_REFERENCE}
        </pre>
      </DisclosurePanel>

      <div className="flex gap-4 mt-8">
        <button
          onClick={onImport}
          className="flex-1 bg-cyan-500 text-slate-950 font-bold py-3.5 px-4 rounded-full active:scale-[0.98] transition-all uppercase text-[12px] tracking-[0.24em] shadow-[0_0_20px_rgba(34,211,238,0.28)] hover:bg-cyan-400"
        >
          Execute Import
        </button>
        <button
          onClick={onLoadSample}
          className="px-6 py-3.5 bg-white/5 text-slate-200 font-bold rounded-full border border-white/10 hover:bg-white/10 active:scale-[0.98] transition-all uppercase text-[12px] tracking-[0.24em] backdrop-blur-xl"
        >
          Load Test Data
        </button>
      </div>
    </div>
  );
}
