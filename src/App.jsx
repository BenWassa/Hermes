import { useEffect, useMemo, useState } from 'react';
import { BottomNav } from './components/BottomNav';
import { SAMPLE_BRIEFING } from './data/sampleBriefing';
import { useLocalStorage } from './hooks/useLocalStorage';
import { signInWithGoogle, signOutUser, subscribeToAuthState } from './lib/firebase';
import { getTodayId } from './utils/date';
import { sanitizeJsonInput } from './utils/json';
import { AddBriefingView } from './views/AddBriefingView';
import { ArchiveView } from './views/ArchiveView';
import { HomeView } from './views/HomeView';
import { OnboardingView } from './views/OnboardingView';
import { SearchView } from './views/SearchView';

const ALLOWED_UIDS = new Set(['aavtqWTiNUZk5NQpDJkvo9IIqh02']);

export default function App() {
  const [authReady, setAuthReady] = useState(false);
  const [user, setUser] = useState(null);
  const [authError, setAuthError] = useState('');
  const [isSigningIn, setIsSigningIn] = useState(false);
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

  useEffect(() => {
    const unsubscribe = subscribeToAuthState((nextUser) => {
      setAuthReady(true);
      setIsSigningIn(false);
      if (!nextUser) {
        setUser(null);
        return;
      }

      if (!ALLOWED_UIDS.has(nextUser.uid)) {
        setUser(null);
        setAuthError(`This account is not authorized for Hermes. Signed in UID: ${nextUser.uid}`);
        signOutUser().catch(() => {});
        return;
      }

      setUser(nextUser);
      setAuthError('');
    });

    return unsubscribe;
  }, []);

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
      const sanitizedInput = sanitizeJsonInput(jsonInput);
      const parsed = JSON.parse(sanitizedInput);

      if (!parsed.id) {
        throw new Error('Missing required field: "id" (Format: YYYY-MM-DD)');
      }
      if (!parsed.date) {
        throw new Error('Missing required field: "date" (Display date string)');
      }
      if (!parsed.today_in_60_seconds || !Array.isArray(parsed.today_in_60_seconds)) {
        throw new Error(
          'Missing or invalid required field: "today_in_60_seconds" (Must be an array of { icon, headline })'
        );
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
      if (parsed.id === getTodayId()) {
        setViewingDateId(null);
        setCurrentView('home');
      } else {
        setViewingDateId(parsed.id);
        setCurrentView('archive');
      }
    } catch (importError) {
      setError(
        importError.message ||
          'Invalid JSON syntax. Check for malformed structure or unsupported pasted formatting.'
      );
    }
  };

  const loadSample = () => {
    setJsonInput(JSON.stringify(SAMPLE_BRIEFING, null, 2));
    setError('');
  };

  const handleGoogleSignIn = async () => {
    setAuthError('');
    setIsSigningIn(true);

    try {
      await signInWithGoogle();
    } catch (signInError) {
      setAuthError(signInError.message || 'Google sign-in failed. Check Firebase Auth provider settings and try again.');
      setIsSigningIn(false);
    }
  };

  if (!authReady) {
    return (
      <div className="flex min-h-screen items-center justify-center px-6 text-center">
        <div className="space-y-3">
          <div className="text-[10px] font-mono font-bold uppercase tracking-[0.32em] text-cyan-400/80">
            Hermes Access Gate
          </div>
          <div className="text-2xl font-extrabold uppercase tracking-tight stark-gradient-text">Authenticating</div>
          <div className="text-[13px] text-slate-500">Checking active Firebase session...</div>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen font-sans text-slate-50 selection:bg-cyan-400/20 selection:text-white">
        <OnboardingView isSigningIn={isSigningIn} error={authError} onSignIn={handleGoogleSignIn} />
      </div>
    );
  }

  return (
    <div className="min-h-screen font-sans text-slate-50 selection:bg-cyan-400/20 selection:text-white">
      <main className="px-4 pb-32 md:px-6">
        {currentView === 'home' && (
          <HomeView
            activeBriefing={activeBriefing}
            latestBriefing={latestBriefing}
            onGoAdd={() => setCurrentView('add')}
            onOpenBriefing={openBriefing}
          />
        )}

        {currentView === 'archive' && (
          <ArchiveView briefings={briefings} onOpenBriefing={openBriefing} onAdd={() => setCurrentView('add')} />
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
