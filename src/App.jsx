import { useMemo, useState } from 'react';
import { BottomNav } from './components/BottomNav';
import { SAMPLE_BRIEFING } from './data/sampleBriefing';
import { useLocalStorage } from './hooks/useLocalStorage';
import { getTodayId } from './utils/date';
import { AddBriefingView } from './views/AddBriefingView';
import { ArchiveView } from './views/ArchiveView';
import { HomeView } from './views/HomeView';
import { SearchView } from './views/SearchView';

export default function App() {
  const [briefings, setBriefings] = useLocalStorage('globalbrief_data', []);
  const [currentView, setCurrentView] = useState('home');
  const [viewingDateId, setViewingDateId] = useState(null);
  const [jsonInput, setJsonInput] = useState('');
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');

  const todayBriefing = briefings.find((briefing) => briefing.id === getTodayId());
  const activeBriefing = viewingDateId
    ? briefings.find((briefing) => briefing.id === viewingDateId)
    : todayBriefing;

  const latestBriefing = briefings.length > 0 ? briefings[0] : null;

  const results = useMemo(() => {
    if (!query.trim()) return [];
    const normalizedQuery = query.toLowerCase();
    return briefings.filter((briefing) =>
      JSON.stringify(briefing).toLowerCase().includes(normalizedQuery)
    );
  }, [briefings, query]);

  const openBriefing = (briefingId) => {
    setViewingDateId(briefingId);
    setCurrentView('home');
  };

  const selectView = (view) => {
    setCurrentView(view);
    if (view === 'home') {
      setViewingDateId(null);
    }
  };

  const handleImport = () => {
    try {
      setError('');
      const parsed = JSON.parse(jsonInput);

      if (!parsed.id || !parsed.date || !parsed.today_in_60_seconds) {
        throw new Error('Invalid format: missing required fields (id, date, today_in_60_seconds)');
      }

      setBriefings((existing) => {
        const existingIndex = existing.findIndex((briefing) => briefing.id === parsed.id);
        if (existingIndex >= 0) {
          const updated = [...existing];
          updated[existingIndex] = parsed;
          return updated.sort((a, b) => new Date(b.id) - new Date(a.id));
        }
        return [parsed, ...existing].sort((a, b) => new Date(b.id) - new Date(a.id));
      });

      setJsonInput('');
      setViewingDateId(parsed.id);
      setCurrentView('home');
    } catch (importError) {
      setError(importError.message || 'Invalid JSON syntax. Please check your format.');
    }
  };

  const loadSample = () => {
    setJsonInput(JSON.stringify(SAMPLE_BRIEFING, null, 2));
    setError('');
  };

  return (
    <div className="min-h-screen bg-slate-50/70 dark:bg-slate-950 font-sans selection:bg-amber-100 dark:selection:bg-amber-900/50">
      <main className="px-4 md:px-6">
        {currentView === 'home' && (
          <HomeView
            activeBriefing={activeBriefing}
            latestBriefing={latestBriefing}
            onGoAdd={() => setCurrentView('add')}
            onOpenBriefing={openBriefing}
          />
        )}

        {currentView === 'archive' && (
          <ArchiveView briefings={briefings} onOpenBriefing={openBriefing} />
        )}

        {currentView === 'search' && (
          <SearchView
            query={query}
            results={results}
            onQueryChange={setQuery}
            onOpenBriefing={openBriefing}
          />
        )}

        {currentView === 'add' && (
          <AddBriefingView
            jsonInput={jsonInput}
            error={error}
            onJsonChange={setJsonInput}
            onImport={handleImport}
            onLoadSample={loadSample}
          />
        )}
      </main>

      <BottomNav currentView={currentView} viewingDateId={viewingDateId} onSelectView={selectView} />
    </div>
  );
}
