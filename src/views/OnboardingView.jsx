import { AlertTriangle, LockKeyhole, LogIn } from 'lucide-react';

export function OnboardingView({ isSigningIn, error, onSignIn }) {
  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-6 pb-24 pt-10 text-center">
      <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border border-cyan-500/20 bg-cyan-950/40 text-cyan-400 shadow-[0_0_24px_rgba(34,211,238,0.16)] backdrop-blur-md">
        <LockKeyhole size={30} strokeWidth={1.75} />
      </div>

      <div className="mb-8 space-y-3">
        <div className="text-[10px] font-mono font-bold uppercase tracking-[0.32em] text-cyan-400/80">
          Hermes Access Gate
        </div>
        <h1 className="text-4xl font-extrabold uppercase tracking-tight stark-gradient-text drop-shadow-[0_0_15px_rgba(34,211,238,0.35)]">
          Hermes
        </h1>
        <p className="text-[14px] font-medium leading-relaxed text-slate-400">
          Sign in with Google to unlock the intelligence console. If your session expires or authentication fails, Hermes returns here automatically.
        </p>
      </div>

      {error ? (
        <div className="mb-6 flex w-full items-start gap-3 rounded-2xl border border-red-500/20 bg-red-950/20 p-4 text-left text-red-300 shadow-[0_0_20px_rgba(239,68,68,0.08)] backdrop-blur-md">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-red-400" />
          <div className="text-[12px] leading-relaxed">{error}</div>
        </div>
      ) : null}

      <button
        type="button"
        onClick={onSignIn}
        disabled={isSigningIn}
        className="flex w-full items-center justify-center gap-3 rounded-full bg-cyan-500 px-6 py-4 text-[12px] font-bold uppercase tracking-[0.24em] text-slate-950 shadow-[0_0_24px_rgba(34,211,238,0.24)] transition-all hover:bg-cyan-400 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-70"
      >
        <LogIn size={18} strokeWidth={2.5} />
        {isSigningIn ? 'Authenticating' : 'Continue With Google'}
      </button>

      <div className="mt-5 text-[11px] font-mono uppercase tracking-[0.22em] text-slate-500">
        Static app hosted on Firebase Hosting
      </div>
    </div>
  );
}
