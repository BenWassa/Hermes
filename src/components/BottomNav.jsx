import { Home, Archive, Layers, Search } from 'lucide-react';

export function BottomNav({ currentView, viewingDateId, synthesesCount, onSelectView }) {
  const todayActive = currentView === 'home' && !viewingDateId;
  const archiveActive = currentView === 'archive' || currentView === 'story' || Boolean(viewingDateId);
  const searchActive = currentView === 'search';
  const synthesisActive = currentView === 'synthesis';

  return (
    <nav
      className="fixed left-0 w-full z-50 px-4 pointer-events-none"
      style={{ bottom: 'max(1.5rem, env(safe-area-inset-bottom))' }}
    >
      <div className="max-w-md mx-auto pointer-events-auto">
        <div className="grid grid-cols-4 items-end gap-1 px-2 py-2 bg-slate-950/80 backdrop-blur-2xl border border-white/10 rounded-full shadow-[0_20px_40px_rgba(0,0,0,0.5),_0_0_20px_rgba(34,211,238,0.1)]">
          <NavButton icon={Home} label="Today" isActive={todayActive} onClick={() => onSelectView('home')} />
          <NavButton
            icon={Layers}
            label="Synthesis"
            isActive={synthesisActive}
            onClick={() => onSelectView('synthesis')}
          />
          <NavButton
            icon={Archive}
            label="Archive"
            isActive={archiveActive}
            onClick={() => onSelectView('archive')}
          />
          <NavButton icon={Search} label="Search" isActive={searchActive} onClick={() => onSelectView('search')} />
        </div>
      </div>
    </nav>
  );
}

function NavButton({ icon: Icon, label, isActive, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className={`min-w-0 h-14 rounded-full flex flex-col items-center justify-center gap-1 transition-all duration-300 ${
        isActive ? 'text-cyan-400 bg-cyan-400/10' : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
      }`}
    >
      <Icon
        size={20}
        strokeWidth={isActive ? 2.5 : 1.5}
        className={isActive ? 'drop-shadow-[0_0_8px_rgba(34,211,238,0.8)]' : ''}
      />
      <span className={`text-[9px] uppercase tracking-[0.22em] ${isActive ? 'text-cyan-300' : 'text-slate-500'}`}>
        {label}
      </span>
    </button>
  );
}
