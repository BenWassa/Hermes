import { useEffect, useState } from 'react';
import { Database, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import { DisclosurePanel } from '../components/DisclosurePanel';
import { sanitizeJsonInput, validateAmplifier, validateDailyBriefing, validateSynthesis } from '../utils/json';

const SCHEMA_REFERENCE = `{
  "id": "2026-03-13",
  "date": "March 13, 2026",
  "system_status": { "condition": "ELEVATED", "indicator": "VOLATILE" },
  "today_in_60_seconds": [
    {
      "icon": "🛢️",
      "headline": "Oil volatility spikes",
      "domain": "ENERGY",
      "summary": "Optional apex summary",
      "status": "ESCALATING",
      "target": "Strait of Hormuz",
      "metric": "+17.1% VOL"
    }
  ],
  "what_changed": {
    "new_stories": ["story-hormuz-coalition"],
    "escalated": ["story-fx-dollar-pressure"],
    "stabilized": [],
    "resolved": []
  },
  "major_developments": [
    {
      "id": "dev-1",
      "story_id": "story-hormuz-coalition",
      "domain": "ENERGY",
      "headline": "Oil Shock and War Risk",
      "driver": "Iran naval posture shift following US carrier redeployment",
      "change_type": "escalating",
      "story_stage": "active",
      "tags": ["iran", "energy", "strait-of-hormuz"],
    }
  ]
}`;

export function AddBriefingView({
  jsonInput,
  error: submitError,
  isImporting = false,
  onJsonChange,
  onImport,
  onLoadSample
}) {
  const [liveStatus, setLiveStatus] = useState({ type: '', message: '', warnings: [] });

  useEffect(() => {
    const timer = setTimeout(() => {
      if (!jsonInput.trim()) {
        setLiveStatus({ type: '', message: '', warnings: [] });
        return;
      }

      try {
        const parsed = JSON.parse(sanitizeJsonInput(jsonInput));

        if (parsed.type === 'synthesis') {
          const { valid, errors, warnings } = validateSynthesis(parsed);
          if (!valid) {
            setLiveStatus({ type: 'error', message: `Import errors: ${errors.join('; ')}`, warnings });
          } else {
            setLiveStatus({ type: 'success', message: 'Schema valid — ready to import JSON.', warnings });
          }
          return;
        }

        if (parsed.type === 'amplifier') {
          const { valid, errors, warnings } = validateAmplifier(parsed);
          if (!valid) {
            setLiveStatus({ type: 'error', message: `Import errors: ${errors.join('; ')}`, warnings });
          } else {
            setLiveStatus({ type: 'success', message: `Schema valid — ready to import amplifier ${parsed.id}.`, warnings });
          }
          return;
        }

        if (Array.isArray(parsed.briefings) || Array.isArray(parsed.syntheses) || Array.isArray(parsed.amplifiers)) {
          const briefingCount = Array.isArray(parsed.briefings) ? parsed.briefings.length : 0;
          const synthesisCount = Array.isArray(parsed.syntheses) ? parsed.syntheses.length : 0;
          const amplifierCount = Array.isArray(parsed.amplifiers) ? parsed.amplifiers.length : 0;
          const totalCount = briefingCount + synthesisCount + amplifierCount;

          if (totalCount === 0) {
            setLiveStatus({ type: 'warning', message: 'Valid JSON, but the archive contains no importable records.', warnings: [] });
            return;
          }
          setLiveStatus({
            type: 'success',
            message: `Archive valid. Ready to import ${briefingCount} briefing${briefingCount === 1 ? '' : 's'}, ${amplifierCount} amplifier${amplifierCount === 1 ? '' : 's'}, and ${synthesisCount} synthesis record${synthesisCount === 1 ? '' : 's'}.`,
            warnings: []
          });
          return;
        }

        const { valid, errors, warnings } = validateDailyBriefing(parsed);
        if (!valid) {
          setLiveStatus({ type: 'error', message: `Missing required fields: ${errors.join('; ')}`, warnings });
        } else {
          setLiveStatus({
            type: 'success',
            message: `Schema valid — ready to import ${parsed.id}.`,
            warnings
          });
        }
      } catch {
        setLiveStatus({
          type: 'error',
          message: 'Invalid JSON syntax — check for missing commas or unclosed brackets.',
          warnings: []
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
        <div className="mb-4 space-y-2">
          <div
            className={`flex items-start gap-3 rounded-2xl border p-4 backdrop-blur-md transition-colors ${
              liveStatus.type === 'success'
                ? 'border-emerald-500/20 bg-emerald-950/20 text-emerald-300 shadow-[0_0_20px_rgba(16,185,129,0.08)]'
                : liveStatus.type === 'warning'
                  ? 'border-amber-500/20 bg-amber-950/20 text-amber-300 shadow-[0_0_20px_rgba(245,158,11,0.08)]'
                  : 'border-red-500/20 bg-red-950/20 text-red-300 shadow-[0_0_20px_rgba(239,68,68,0.08)]'
            }`}
          >
            {liveStatus.type === 'success' ? (
              <CheckCircle size={18} className="mt-0.5 shrink-0 text-emerald-400" />
            ) : liveStatus.type === 'warning' ? (
              <Info size={18} className="mt-0.5 shrink-0 text-amber-400" />
            ) : (
              <AlertTriangle size={18} className="mt-0.5 shrink-0 text-red-400" />
            )}
            <div className="text-[12px] font-mono font-medium leading-relaxed">{liveStatus.message}</div>
          </div>
          {liveStatus.warnings?.length > 0 ? (
            <div className="rounded-xl border border-amber-500/15 bg-amber-950/10 px-4 py-3">
              <div className="text-[9px] font-mono font-bold uppercase tracking-[0.22em] text-amber-500/70 mb-1.5">Schema Warnings</div>
              <ul className="space-y-1">
                {liveStatus.warnings.map((w, i) => (
                  <li key={i} className="text-[11px] font-mono text-amber-300/70 leading-relaxed flex gap-2">
                    <span className="text-amber-500/40 shrink-0">›</span>{w}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
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

      <div className="space-y-3">
        <DisclosurePanel
          title="Daily Briefing Schema"
          eyebrow="Format Reference"
          accentClassName="text-slate-400"
        >
          <pre className="overflow-x-auto rounded-xl border border-white/5 bg-slate-950/50 p-4 font-mono text-[11px] text-slate-300">
            {SCHEMA_REFERENCE}
          </pre>
        </DisclosurePanel>
      </div>

      <div className="flex gap-4 mt-8">
        <button
          onClick={onImport}
          disabled={isImporting}
          className="flex-1 bg-cyan-500 text-slate-950 font-bold py-3.5 px-4 rounded-full active:scale-[0.98] transition-all uppercase text-[12px] tracking-[0.24em] shadow-[0_0_20px_rgba(34,211,238,0.28)] hover:bg-cyan-400"
        >
          {isImporting ? 'Syncing Import' : 'Execute Import'}
        </button>
        <button
          onClick={onLoadSample}
          disabled={isImporting}
          className="px-6 py-3.5 bg-white/5 text-slate-200 font-bold rounded-full border border-white/10 hover:bg-white/10 active:scale-[0.98] transition-all uppercase text-[12px] tracking-[0.24em] backdrop-blur-xl"
        >
          Load Test Data
        </button>
      </div>
    </div>
  );
}
