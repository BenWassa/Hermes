import React, { useState } from 'react';
import {
  Home,
  Archive,
  Search,
  PlusCircle,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Clock,
  ArrowRight
} from 'lucide-react';

const SAMPLE_JSON = {
  id: '2026-03-09',
  date: 'March 9, 2026',
  today_in_60_seconds: [
    { icon: '🛢️', headline: 'Oil volatility spikes' },
    { icon: '📉', headline: 'Markets reprice inflation risk' },
    { icon: '🤖', headline: 'China accelerates AI push' },
    { icon: '⚖️', headline: 'Pentagon-AI tension emerges' }
  ],
  major_developments: [
    {
      id: 'dev-1',
      icon: '🛢️',
      headline: 'Oil Shock and War Risk',
      executive_summary:
        'Oil surged nearly 30% before reversing as geopolitical tensions escalated.',
      key_facts: [
        'Brent briefly crossed $100',
        'De-escalation signals caused reversal',
        'Market volatility spread to equities'
      ],
      sources: ['Reuters', 'Bloomberg', 'FT']
    },
    {
      id: 'dev-2',
      icon: '🤖',
      headline: 'Sovereign AI Compute Race',
      executive_summary:
        'Nations are increasingly treating high-tier compute clusters as critical national infrastructure.',
      key_facts: [
        'New export controls proposed on advanced chips',
        'Middle Eastern sovereign wealth funds redirecting capital to domestic datacenters',
        'Talent acquisition becomes state-level priority'
      ],
      sources: ['WSJ', 'TechCrunch', 'State Dept']
    }
  ],
  analyst_consensus: {
    consensus: [
      'Energy shock could delay rate cuts globally.',
      'Defense and compute spending will remain non-cyclical.'
    ],
    friction: [
      'Some analysts believe the oil spike will reverse rapidly if conflict cools.',
      "Disagreement on whether the ECB will follow the Fed's hawkish tilt."
    ]
  },
  strategic_context: [
    'Energy shocks are reintroducing geopolitics into macroeconomic expectations.',
    'Persistent oil elevation could force central banks to maintain tighter policy despite slowing growth.',
    'The intersection of AI infrastructure demands and energy scarcity is becoming the defining macroeconomic theme of the decade.'
  ],
  watchlist:
    'Strait of Hormuz shipping flows over the next 48 hours may determine whether energy volatility persists and bleeds into core inflation metrics.'
};

function useLocalStorage(key, initialValue) {
  const [storedValue, setStoredValue] = useState(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error(error);
      return initialValue;
    }
  });

  const setValue = (value) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error(error);
    }
  };

  return [storedValue, setValue];
}

function DevelopmentCard({ dev }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl p-4 shadow-sm border border-slate-100 dark:border-slate-800 transition-all duration-200">
      <div
        className="flex items-start justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex gap-3 items-start">
          <div className="text-2xl mt-0.5">{dev.icon}</div>
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-lg leading-tight mb-1">
              {dev.headline}
            </h3>
            <p className="text-slate-600 dark:text-slate-400 text-sm leading-snug">
              {dev.executive_summary}
            </p>
          </div>
        </div>
        <div className="ml-2 text-slate-400">
          {expanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </div>
      </div>

      {expanded && (
        <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Key Facts</h4>
          <ul className="space-y-2 mb-4">
            {dev.key_facts.map((fact, idx) => (
              <li key={idx} className="flex gap-2 text-sm text-slate-700 dark:text-slate-300">
                <span className="text-slate-400">•</span>
                <span>{fact}</span>
              </li>
            ))}
          </ul>

          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Sources</h4>
          <div className="flex flex-wrap gap-2 text-xs text-slate-500">
            {dev.sources.map((source, idx) => (
              <span key={idx} className="bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-md">
                {source}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function BriefingDisplay({ data }) {
  if (!data) return null;

  return (
    <div className="pb-24 max-w-2xl mx-auto space-y-8">
      <header className="pt-6 pb-2 border-b border-slate-200 dark:border-slate-800">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">GlobalBrief</h1>
        <p className="text-sm font-medium text-slate-500 uppercase tracking-widest mt-1">
          Daily Intelligence Briefing
        </p>
        <div className="mt-4 inline-flex items-center gap-2 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 px-3 py-1.5 rounded-full text-sm font-medium">
          <Clock size={14} />
          {data.date}
        </div>
      </header>

      <section>
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">
          Today in 60 Seconds
        </h2>
        <div className="grid grid-cols-2 gap-3">
          {data.today_in_60_seconds.map((item, idx) => (
            <div
              key={idx}
              className="bg-white dark:bg-slate-900 p-3 rounded-xl shadow-sm border border-slate-100 dark:border-slate-800 flex flex-col gap-2 active:scale-95 transition-transform"
            >
              <span className="text-2xl">{item.icon}</span>
              <span className="text-sm font-medium text-slate-800 dark:text-slate-200 leading-tight">
                {item.headline}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">
          Major Developments
        </h2>
        <div className="space-y-3">
          {data.major_developments.map((dev) => (
            <DevelopmentCard key={dev.id} dev={dev} />
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">
          Analyst Consensus & Disagreement
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="bg-slate-50 dark:bg-slate-900/50 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
            <h3 className="text-xs font-bold uppercase text-emerald-600 dark:text-emerald-400 mb-3">
              Consensus
            </h3>
            <ul className="space-y-3">
              {data.analyst_consensus.consensus.map((item, idx) => (
                <li key={idx} className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="bg-slate-50 dark:bg-slate-900/50 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
            <h3 className="text-xs font-bold uppercase text-rose-600 dark:text-rose-400 mb-3">
              Points of Friction
            </h3>
            <ul className="space-y-3">
              {data.analyst_consensus.friction.map((item, idx) => (
                <li key={idx} className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">
          Strategic Context
        </h2>
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl shadow-sm border border-slate-100 dark:border-slate-800">
          <div className="max-w-none">
            {data.strategic_context.map((para, idx) => (
              <p
                key={idx}
                className="text-slate-700 dark:text-slate-300 leading-relaxed mb-4 last:mb-0 text-[15px]"
              >
                {para}
              </p>
            ))}
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">Watchlist</h2>
        <div className="bg-amber-50 dark:bg-amber-950/30 p-5 rounded-xl border border-amber-100 dark:border-amber-900/50 border-l-4 border-l-amber-500">
          <p className="text-amber-900 dark:text-amber-200 font-medium leading-relaxed">{data.watchlist}</p>
        </div>
      </section>
    </div>
  );
}

export default function App() {
  const [briefings, setBriefings] = useLocalStorage('globalbrief_data', []);
  const [currentView, setCurrentView] = useState('home');
  const [viewingDateId, setViewingDateId] = useState(null);
  const [jsonInput, setJsonInput] = useState('');
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');

  const getTodayId = () => new Date().toISOString().split('T')[0];

  const todayBriefing = briefings.find((b) => b.id === getTodayId());
  const activeBriefing = viewingDateId
    ? briefings.find((b) => b.id === viewingDateId)
    : todayBriefing;

  const handleImport = () => {
    try {
      setError('');
      const parsed = JSON.parse(jsonInput);

      if (!parsed.id || !parsed.date || !parsed.today_in_60_seconds) {
        throw new Error('Invalid format: missing required fields (id, date, today_in_60_seconds)');
      }

      const existingIdx = briefings.findIndex((b) => b.id === parsed.id);
      let newBriefings = [...briefings];

      if (existingIdx >= 0) {
        newBriefings[existingIdx] = parsed;
      } else {
        newBriefings = [parsed, ...newBriefings].sort((a, b) => new Date(b.id) - new Date(a.id));
      }

      setBriefings(newBriefings);
      setJsonInput('');
      setViewingDateId(parsed.id);
      setCurrentView('home');
    } catch (err) {
      setError(err.message || 'Invalid JSON syntax. Please check your format.');
    }
  };

  const loadSample = () => {
    setJsonInput(JSON.stringify(SAMPLE_JSON, null, 2));
    setError('');
  };

  const renderHome = () => {
    if (activeBriefing) {
      return <BriefingDisplay data={activeBriefing} />;
    }

    const yesterdayBriefing = briefings.length > 0 ? briefings[0] : null;

    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] px-4 max-w-md mx-auto text-center space-y-6">
        <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-2xl flex items-center justify-center mb-2">
          <AlertCircle className="text-slate-400" size={32} />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">No Briefing Loaded</h2>
          <p className="text-slate-500 dark:text-slate-400 mb-8">
            Your intelligence panel is currently empty for today. Paste your generated JSON to
            populate the dashboard.
          </p>
        </div>

        <button
          onClick={() => setCurrentView('add')}
          className="w-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-semibold py-4 px-6 rounded-xl shadow-md active:scale-[0.98] transition-all"
        >
          Add Today's Briefing
        </button>

        {yesterdayBriefing && (
          <button
            onClick={() => {
              setViewingDateId(yesterdayBriefing.id);
            }}
            className="flex items-center justify-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors py-2"
          >
            View previous briefing
            <ArrowRight size={16} />
          </button>
        )}
      </div>
    );
  };

  const renderArchive = () => (
    <div className="pb-24 max-w-2xl mx-auto pt-6 px-4">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-6">Intelligence Archive</h1>
      {briefings.length === 0 ? (
        <p className="text-slate-500">No historical briefings available.</p>
      ) : (
        <div className="space-y-3">
          {briefings.map((b) => (
            <button
              key={b.id}
              onClick={() => {
                setViewingDateId(b.id);
                setCurrentView('home');
              }}
              className="w-full flex items-center justify-between bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-100 dark:border-slate-800 shadow-sm active:scale-[0.98] transition-all text-left"
            >
              <div>
                <div className="font-semibold text-slate-900 dark:text-white">{b.date}</div>
                <div className="text-sm text-slate-500 truncate max-w-[250px] mt-1">
                  {b.today_in_60_seconds[0]?.headline} &bull; {b.today_in_60_seconds[1]?.headline}
                </div>
              </div>
              <ChevronDown size={20} className="text-slate-400 -rotate-90" />
            </button>
          ))}
        </div>
      )}
    </div>
  );

  const results =
    query.trim() === ''
      ? []
      : briefings.filter((b) => JSON.stringify(b).toLowerCase().includes(query.toLowerCase()));

  const renderSearch = () => (
    <div className="pb-24 max-w-2xl mx-auto pt-6 px-4">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-6">Search Database</h1>
      <div className="relative mb-8">
        <Search className="absolute left-3 top-3.5 text-slate-400" size={20} />
        <input
          type="text"
          placeholder="Search by keyword, tag, or theme..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
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
            results.map((b) => (
              <button
                key={b.id}
                onClick={() => {
                  setViewingDateId(b.id);
                  setCurrentView('home');
                }}
                className="w-full flex flex-col gap-2 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-100 dark:border-slate-800 shadow-sm text-left active:scale-[0.98] transition-transform"
              >
                <div className="flex justify-between items-center w-full">
                  <span className="font-semibold text-slate-900 dark:text-white">{b.date}</span>
                  <ArrowRight size={16} className="text-slate-400" />
                </div>
                <div className="text-sm text-slate-600 dark:text-slate-400 line-clamp-2">
                  {b.major_developments?.map((d) => d.headline).join(' · ')}
                </div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );

  const renderAdd = () => (
    <div className="pb-24 max-w-2xl mx-auto pt-6 px-4">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">Import Intelligence</h1>
      <p className="text-slate-500 mb-6 text-sm">
        Paste the JSON generated from your daily prompt below.
      </p>

      {error && (
        <div className="bg-rose-50 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400 p-4 rounded-xl mb-4 text-sm font-medium border border-rose-100 dark:border-rose-900/50">
          {error}
        </div>
      )}

      <textarea
        value={jsonInput}
        onChange={(e) => setJsonInput(e.target.value)}
        placeholder="Paste JSON here..."
        className="w-full h-64 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 font-mono text-xs text-slate-800 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-900 dark:focus:ring-slate-500 shadow-inner resize-none mb-4"
        spellCheck={false}
      />

      <div className="flex gap-3">
        <button
          onClick={handleImport}
          className="flex-1 bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-semibold py-3 px-4 rounded-xl shadow-md active:scale-[0.98] transition-all"
        >
          Import Briefing
        </button>
        <button
          onClick={loadSample}
          className="px-4 py-3 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium rounded-xl border border-slate-200 dark:border-slate-700 active:scale-[0.98] transition-all"
        >
          Load Sample
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50/70 dark:bg-slate-950 font-sans selection:bg-amber-100 dark:selection:bg-amber-900/50">
      <main className="px-4 md:px-6">
        {currentView === 'home' && renderHome()}
        {currentView === 'archive' && renderArchive()}
        {currentView === 'search' && renderSearch()}
        {currentView === 'add' && renderAdd()}
      </main>

      <nav className="fixed bottom-0 w-full bg-white/85 dark:bg-slate-950/85 backdrop-blur-md border-t border-slate-200 dark:border-slate-800 shadow-[0_-4px_20px_rgba(0,0,0,0.02)] z-50">
        <div className="max-w-md mx-auto flex justify-between items-center px-6 py-3">
          <button
            onClick={() => {
              setCurrentView('home');
              setViewingDateId(null);
            }}
            className={`flex flex-col items-center gap-1 transition-colors ${
              currentView === 'home' && !viewingDateId
                ? 'text-slate-900 dark:text-white'
                : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
            }`}
          >
            <Home size={24} strokeWidth={currentView === 'home' && !viewingDateId ? 2.5 : 2} />
            <span className="text-[10px] font-medium tracking-wide">Today</span>
          </button>

          <button
            onClick={() => setCurrentView('archive')}
            className={`flex flex-col items-center gap-1 transition-colors ${
              currentView === 'archive' || viewingDateId
                ? 'text-slate-900 dark:text-white'
                : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
            }`}
          >
            <Archive size={24} strokeWidth={currentView === 'archive' || viewingDateId ? 2.5 : 2} />
            <span className="text-[10px] font-medium tracking-wide">Archive</span>
          </button>

          <button
            onClick={() => setCurrentView('search')}
            className={`flex flex-col items-center gap-1 transition-colors ${
              currentView === 'search'
                ? 'text-slate-900 dark:text-white'
                : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
            }`}
          >
            <Search size={24} strokeWidth={currentView === 'search' ? 2.5 : 2} />
            <span className="text-[10px] font-medium tracking-wide">Search</span>
          </button>

          <button
            onClick={() => setCurrentView('add')}
            className={`flex flex-col items-center gap-1 transition-colors ${
              currentView === 'add'
                ? 'text-slate-900 dark:text-white'
                : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
            }`}
          >
            <PlusCircle size={24} strokeWidth={currentView === 'add' ? 2.5 : 2} />
            <span className="text-[10px] font-medium tracking-wide">Add</span>
          </button>
        </div>
      </nav>
    </div>
  );
}
