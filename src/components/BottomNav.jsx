import { Home, Archive, Search, PlusSquare } from 'lucide-react';

export function BottomNav({ currentView, viewingDateId, onSelectView }) {
  const todayActive = currentView === 'home' && !viewingDateId;
  const archiveActive = currentView === 'archive' || Boolean(viewingDateId);
  const searchActive = currentView === 'search';
  const addActive = currentView === 'add';

  return (
    <nav className="fixed bottom-0 w-full bg-[#f8fafc] dark:bg-[#0B0F19] border-t-2 border-slate-900 dark:border-white z-50">
      <div className="max-w-md mx-auto flex justify-between items-center px-4 py-3">
        <NavButton icon={Home} label="Today" isActive={todayActive} onClick={() => onSelectView('home')} />
        <NavButton icon={Archive} label="Archive" isActive={archiveActive} onClick={() => onSelectView('archive')} />
        <NavButton icon={Search} label="Search" isActive={searchActive} onClick={() => onSelectView('search')} />
        <NavButton icon={PlusSquare} label="Import" isActive={addActive} onClick={() => onSelectView('add')} />
      </div>
    </nav>
  );
}

function NavButton({ icon: Icon, label, isActive, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`flex flex-col items-center gap-1.5 transition-all px-4 py-2 ${
        isActive
          ? 'text-slate-900 dark:text-white'
          : 'text-slate-400 dark:text-slate-600 hover:text-slate-600 dark:hover:text-slate-400'
      }`}
    >
      <Icon size={22} strokeWidth={isActive ? 2.5 : 1.5} className={isActive ? 'opacity-100' : 'opacity-70'} />
      <span className={`text-[9px] font-mono uppercase tracking-widest ${isActive ? 'font-bold' : 'font-medium'}`}>
        {label}
      </span>
    </button>
  );
}
