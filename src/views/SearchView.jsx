import { Search, ArrowRight } from 'lucide-react';

export function SearchView({ query, results, onQueryChange, onOpenBriefing }) {
  return (
    <div className="pb-24 max-w-2xl mx-auto pt-6 px-4">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-6">Search Database</h1>
      <div className="relative mb-8">
        <Search className="absolute left-3 top-3.5 text-slate-400" size={20} />
        <input
          type="text"
          placeholder="Search by keyword, tag, or theme..."
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl py-3 pl-10 pr-4 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-slate-900 dark:focus:ring-slate-500 shadow-sm transition-all"
        />
      </div>

      {query && (
        <div className="space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">
            Results ({results.length})
          </h2>
          {results.length === 0 ? (
            <p className="text-slate-500">No signals found matching your query.</p>
          ) : (
            results.map((briefing) => (
              <button
                key={briefing.id}
                onClick={() => onOpenBriefing(briefing.id)}
                className="w-full flex flex-col gap-2 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-100 dark:border-slate-800 shadow-sm text-left active:scale-[0.98] transition-transform"
              >
                <div className="flex justify-between items-center w-full">
                  <span className="font-semibold text-slate-900 dark:text-white">{briefing.date}</span>
                  <ArrowRight size={16} className="text-slate-400" />
                </div>
                <div className="text-sm text-slate-600 dark:text-slate-400 line-clamp-2">
                  {briefing.major_developments?.map((development) => development.headline).join(' · ')}
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
