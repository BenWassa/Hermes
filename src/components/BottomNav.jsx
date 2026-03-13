import { Home, Archive, Search, PlusCircle } from 'lucide-react';

export function BottomNav({ currentView, viewingDateId, onSelectView }) {
  const todayActive = currentView === 'home' && !viewingDateId;
  const archiveActive = currentView === 'archive' || Boolean(viewingDateId);
  const searchActive = currentView === 'search';
  const addActive = currentView === 'add';

  return (
    <nav className="fixed bottom-0 w-full bg-white/85 dark:bg-slate-950/85 backdrop-blur-md border-t border-slate-200 dark:border-slate-800 shadow-[0_-4px_20px_rgba(0,0,0,0.02)] z-50">
      <div className="max-w-md mx-auto flex justify-between items-center px-6 py-3">
        <button
          onClick={() => onSelectView('home')}
          className={`flex flex-col items-center gap-1 transition-colors ${
            todayActive
              ? 'text-slate-900 dark:text-white'
              : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
          }`}
        >
          <Home size={24} strokeWidth={todayActive ? 2.5 : 2} />
          <span className="text-[10px] font-medium tracking-wide">Today</span>
        </button>

        <button
          onClick={() => onSelectView('archive')}
          className={`flex flex-col items-center gap-1 transition-colors ${
            archiveActive
              ? 'text-slate-900 dark:text-white'
              : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
          }`}
        >
          <Archive size={24} strokeWidth={archiveActive ? 2.5 : 2} />
          <span className="text-[10px] font-medium tracking-wide">Archive</span>
        </button>

        <button
          onClick={() => onSelectView('search')}
          className={`flex flex-col items-center gap-1 transition-colors ${
            searchActive
              ? 'text-slate-900 dark:text-white'
              : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
          }`}
        >
          <Search size={24} strokeWidth={searchActive ? 2.5 : 2} />
          <span className="text-[10px] font-medium tracking-wide">Search</span>
        </button>

        <button
          onClick={() => onSelectView('add')}
          className={`flex flex-col items-center gap-1 transition-colors ${
            addActive
              ? 'text-slate-900 dark:text-white'
              : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
          }`}
        >
          <PlusCircle size={24} strokeWidth={addActive ? 2.5 : 2} />
          <span className="text-[10px] font-medium tracking-wide">Add</span>
        </button>
      </div>
    </nav>
  );
}
