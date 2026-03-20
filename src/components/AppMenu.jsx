import { useEffect } from 'react';
import { Database, Download, LogOut, Trash2, Upload, User, X } from 'lucide-react';

function MenuSection({ icon: Icon, title, children }) {
  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-4 backdrop-blur-xl">
      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-cyan-500/20 bg-cyan-950/40 text-cyan-300">
          <Icon size={18} strokeWidth={2} />
        </div>
        <div className="text-[11px] font-mono font-bold uppercase tracking-[0.24em] text-slate-400">
          {title}
        </div>
      </div>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

function MenuAction({ icon: Icon, label, hint, onClick, tone = 'default' }) {
  const toneClassName =
    tone === 'danger'
      ? 'border-red-500/20 bg-red-950/20 text-red-200 hover:border-red-400/30 hover:bg-red-950/30'
      : 'border-white/10 bg-white/[0.04] text-slate-100 hover:border-cyan-400/30 hover:bg-white/[0.08]';

  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left transition-colors ${toneClassName}`}
    >
      <Icon size={16} strokeWidth={2} className="shrink-0" />
      <div className="min-w-0">
        <div className="text-[13px] font-semibold">{label}</div>
        <div className="mt-1 text-[11px] text-slate-400">{hint}</div>
      </div>
    </button>
  );
}

export function AppMenu({
  isOpen,
  user,
  role,
  version,
  canImport,
  canDelete,
  onClose,
  onSignOut,
  onImport,
  onExport,
  onDeleteAll
}) {
  useEffect(() => {
    if (!isOpen) return undefined;

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50" aria-modal="true" role="dialog">
      <button
        type="button"
        aria-label="Close menu"
        className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm"
        onClick={onClose}
      />

      <aside className="absolute inset-y-0 left-0 flex w-[min(88vw,24rem)] flex-col border-r border-white/10 bg-[linear-gradient(180deg,rgba(8,18,33,0.98),rgba(4,8,15,0.98))] px-4 pb-6 pt-5 shadow-[0_28px_80px_rgba(0,0,0,0.65)]">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <div className="text-[10px] font-mono font-bold uppercase tracking-[0.3em] text-cyan-400/80">
              Hermes
            </div>
            <div className="mt-1 text-xl font-extrabold uppercase tracking-[0.18em] text-slate-50">
              Control
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-2xl border border-white/10 bg-white/[0.04] p-2 text-slate-300 transition-colors hover:border-cyan-400/30 hover:text-white"
          >
            <X size={18} strokeWidth={2.2} />
          </button>
        </div>

        <div className="hide-scrollbar flex-1 space-y-4 overflow-y-auto pr-1">
          <MenuSection icon={User} title="Account">
            <div className="rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3">
              <div className="text-[13px] font-semibold text-slate-100">
                {user?.displayName || 'Authorized User'}
              </div>
              <div className="mt-1 break-all text-[11px] text-slate-400">{user?.email || 'No email available'}</div>
              <div className="mt-2 text-[10px] font-mono uppercase tracking-[0.18em] text-cyan-400/70">
                Role: {role || 'reader'}
              </div>
            </div>
            <MenuAction
              icon={LogOut}
              label="Sign out"
              hint="End the current Firebase session on this device."
              onClick={onSignOut}
            />
          </MenuSection>

          <MenuSection icon={Database} title="Data">
            {canImport ? (
              <MenuAction
                icon={Upload}
                label="Import JSON"
                hint="Load shared briefings or synthesis overlays into Firestore."
                onClick={onImport}
              />
            ) : null}
            <MenuAction
              icon={Download}
              label="Export archive"
              hint="Download the current shared briefings and synthesis overlays."
              onClick={onExport}
            />
            {canDelete ? (
              <MenuAction
                icon={Trash2}
                label="Delete shared data"
                hint="Permanently clear shared briefings and syntheses for all approved users."
                onClick={onDeleteAll}
                tone="danger"
              />
            ) : null}
          </MenuSection>
        </div>

        <div className="mt-6 border-t border-white/10 pt-4 text-[10px] font-mono uppercase tracking-[0.22em] text-slate-500">
          Version {version}
        </div>
      </aside>
    </div>
  );
}
