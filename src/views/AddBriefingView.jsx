export function AddBriefingView({ jsonInput, error, onJsonChange, onImport, onLoadSample }) {
  return (
    <div className="pb-24 max-w-2xl mx-auto pt-6 px-4">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">Import Intelligence</h1>
      <p className="text-slate-500 mb-6 text-sm">Paste the JSON generated from your daily prompt below.</p>

      {error && (
        <div className="bg-rose-50 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400 p-4 rounded-xl mb-4 text-sm font-medium border border-rose-100 dark:border-rose-900/50">
          {error}
        </div>
      )}

      <textarea
        value={jsonInput}
        onChange={(event) => onJsonChange(event.target.value)}
        placeholder="Paste JSON here..."
        className="w-full h-64 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 font-mono text-xs text-slate-800 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-900 dark:focus:ring-slate-500 shadow-inner resize-none mb-4"
        spellCheck={false}
      />

      <div className="flex gap-3">
        <button
          onClick={onImport}
          className="flex-1 bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-semibold py-3 px-4 rounded-xl shadow-md active:scale-[0.98] transition-all"
        >
          Import Briefing
        </button>
        <button
          onClick={onLoadSample}
          className="px-4 py-3 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium rounded-xl border border-slate-200 dark:border-slate-700 active:scale-[0.98] transition-all"
        >
          Load Sample
        </button>
      </div>
    </div>
  );
}
