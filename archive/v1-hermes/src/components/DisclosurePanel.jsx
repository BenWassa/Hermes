import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

export function DisclosurePanel({
  title,
  eyebrow,
  accentClassName,
  defaultOpen = false,
  children
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="w-full flex items-center justify-between gap-4 px-5 py-4 text-left group"
      >
        <div className="min-w-0">
          {eyebrow ? (
            <div className={`text-[10px] font-bold uppercase tracking-[0.24em] mb-1 ${accentClassName}`}>
              {eyebrow}
            </div>
          ) : null}
          <h2 className="text-[14px] font-semibold text-white leading-snug">{title}</h2>
        </div>
        <div className="shrink-0 text-slate-500 group-hover:text-cyan-400 transition-colors">
          {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>

      {open ? <div className="px-5 pb-5 animate-in fade-in slide-in-from-top-2 duration-300">{children}</div> : null}
    </section>
  );
}
