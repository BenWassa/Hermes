import { Home, Archive, Search, Plus } from 'lucide-react';

export function BottomNav({ currentView, viewingDateId, onSelectView }) {
  const todayActive = currentView === 'home' && !viewingDateId;
  const archiveActive = currentView === 'archive' || Boolean(viewingDateId);
  const searchActive = currentView === 'search';
  const addActive = currentView === 'add';

  return (
    <nav className="fixed bottom-6 left-0 w-full z-50 px-4 pointer-events-none">
      <div className="max-w-md mx-auto pointer-events-auto">
        <div className="flex justify-between items-center px-2 py-2 bg-slate-950/80 backdrop-blur-2xl border border-white/10 rounded-full shadow-[0_20px_40px_rgba(0,0,0,0.5),_0_0_20px_rgba(34,211,238,0.1)]">
          <NavButton icon={Home} label="Today" isActive={todayActive} onClick={() => onSelectView('home')} />
          <NavButton icon={Archive} label="Archive" isActive={archiveActive} onClick={() => onSelectView('archive')} />

          <button
            onClick={() => onSelectView('add')}
            aria-label="Import"
            className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 ${
              addActive
                ? 'bg-cyan-500 text-slate-950 shadow-[0_0_20px_rgba(34,211,238,0.6)] scale-110'
                : 'bg-slate-800 text-cyan-400 border border-cyan-500/30 hover:bg-slate-700'
            }`}
          >
            <Plus size={24} strokeWidth={2.5} />
          </button>

          <NavButton icon={Search} label="Search" isActive={searchActive} onClick={() => onSelectView('search')} />
          <div className="w-12" aria-hidden="true"></div>
        </div>
      </div>
    </nav>
  );
}

function NavButton({ icon: Icon, label, isActive, onClick }) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      className={`w-12 h-12 rounded-full flex flex-col items-center justify-center transition-all duration-300 ${
        isActive ? 'text-cyan-400 bg-cyan-400/10' : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
      }`}
    >
      <Icon
        size={22}
        strokeWidth={isActive ? 2.5 : 1.5}
        className={isActive ? 'drop-shadow-[0_0_8px_rgba(34,211,238,0.8)]' : ''}
      />
    </button>
  );
}
