import { Database, AlertTriangle } from 'lucide-react';

export function AddBriefingView({ jsonInput, error, onJsonChange, onImport, onLoadSample }) {
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

      {error && (
        <div className="bg-red-950/20 text-red-300 p-4 mb-6 border border-red-500/20 rounded-2xl flex items-start gap-3 backdrop-blur-md shadow-[0_0_20px_rgba(239,68,68,0.08)]">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-red-400" />
          <div className="text-[12px] font-medium leading-relaxed">{error}</div>
        </div>
      )}

      <div className="relative group">
        <div className="absolute top-0 left-0 w-full h-9 bg-white/10 rounded-t-2xl flex items-center px-4 border border-b-0 border-white/10 backdrop-blur-xl">
          <span className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-400">
            data.json
          </span>
        </div>
        <textarea
          value={jsonInput}
          onChange={(event) => onJsonChange(event.target.value)}
          placeholder="Paste generated JSON schema here..."
          className="w-full h-[400px] mt-9 bg-white/5 border border-white/10 rounded-b-2xl p-4 text-[13px] text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/40 resize-none transition-colors backdrop-blur-xl shadow-[0_12px_40px_rgba(0,0,0,0.2)]"
          spellCheck={false}
        />
      </div>

      <div className="flex gap-4 mt-6">
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
