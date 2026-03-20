import { useEffect, useMemo, useRef, useState } from 'react';
import { Menu } from 'lucide-react';
import { BottomNav } from './components/BottomNav';
import { AppMenu } from './components/AppMenu';
import { SAMPLE_BRIEFING } from './data/sampleBriefing';
import {
  clearSharedContent,
  getAccessRecord,
  signInWithGoogle,
  signOutUser,
  subscribeToAuthState,
  subscribeToBriefings,
  subscribeToSyntheses,
  upsertBriefings,
  upsertSynthesis
} from './lib/firebase';
import { getTodayId } from './utils/date';
import { sanitizeJsonInput, validateDailyBriefing, validateSynthesis } from './utils/json';
import { AddBriefingView } from './views/AddBriefingView';
import { ArchiveView } from './views/ArchiveView';
import { HomeView } from './views/HomeView';
import { OnboardingView } from './views/OnboardingView';
import { SearchView } from './views/SearchView';
import { StoryView } from './views/StoryView';
import { SynthesisView } from './views/SynthesisView';
import packageMetadata from '../package.json';

const APP_VERSION = packageMetadata.version;

function getExportTimestamp() {
  return new Date().toISOString().replace(/[:]/g, '-').replace(/\.\d{3}Z$/, 'Z');
}

function downloadFile(filename, contents, type) {
  const blob = new Blob([contents], { type });
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');

  link.href = objectUrl;
  link.download = filename;
  link.click();

  URL.revokeObjectURL(objectUrl);
}

export default function App() {
  const [authReady, setAuthReady] = useState(false);
  const [accessReady, setAccessReady] = useState(false);
  const [contentReady, setContentReady] = useState(false);
  const [user, setUser] = useState(null);
  const [accessRecord, setAccessRecord] = useState(null);
  const [authError, setAuthError] = useState('');
  const [dataError, setDataError] = useState('');
  const [isSigningIn, setIsSigningIn] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [briefings, setBriefings] = useState([]);
  const [syntheses, setSyntheses] = useState([]);
  const [currentView, setCurrentView] = useState('home');
  const [viewingDateId, setViewingDateId] = useState(null);
  const [viewingStoryId, setViewingStoryId] = useState(null);
  const [jsonInput, setJsonInput] = useState('');
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const fileInputRef = useRef(null);

  const isAdmin = accessRecord?.role === 'admin';
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
    let isCancelled = false;

    const unsubscribe = subscribeToAuthState(async (nextUser) => {
      if (isCancelled) return;

      setAuthReady(true);
      setIsSigningIn(false);
      setDataError('');

      if (!nextUser) {
        setUser(null);
        setAccessRecord(null);
        setAccessReady(true);
        setContentReady(false);
        setBriefings([]);
        setSyntheses([]);
        return;
      }

      setAccessReady(false);
      setContentReady(false);

      try {
        const nextAccessRecord = await getAccessRecord(nextUser.uid);

        if (isCancelled) return;

        if (!nextAccessRecord?.active) {
          setUser(null);
          setAccessRecord(null);
          setAccessReady(true);
          setAuthError(
            nextAccessRecord
              ? 'This account is inactive for Hermes.'
              : `This account is not authorized for Hermes. Signed in UID: ${nextUser.uid}`
          );
          signOutUser().catch(() => {});
          return;
        }

        setUser(nextUser);
        setAccessRecord(nextAccessRecord);
        setAccessReady(true);
        setAuthError('');
      } catch (accessError) {
        if (isCancelled) return;
        setUser(null);
        setAccessRecord(null);
        setAccessReady(true);
        setAuthError(accessError.message || 'Failed to verify Hermes access.');
        signOutUser().catch(() => {});
      }
    });

    return () => {
      isCancelled = true;
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (!user || !accessRecord?.active) {
      return undefined;
    }

    let isCancelled = false;
    let pendingStreams = 2;
    let briefingsInitialized = false;
    let synthesesInitialized = false;

    setContentReady(false);
    setDataError('');

    const markStreamReady = () => {
      pendingStreams -= 1;
      if (!isCancelled && pendingStreams <= 0) {
        setContentReady(true);
      }
    };

    const handleStreamError = (streamLabel) => (streamError) => {
      if (isCancelled) return;
      setDataError(streamError.message || `Failed to load shared ${streamLabel}.`);
      if (streamLabel === 'briefings' && !briefingsInitialized) {
        briefingsInitialized = true;
        markStreamReady();
      }
      if (streamLabel === 'syntheses' && !synthesesInitialized) {
        synthesesInitialized = true;
        markStreamReady();
      }
    };

    const unsubscribeBriefings = subscribeToBriefings(
      (nextBriefings) => {
        if (isCancelled) return;
        setBriefings(nextBriefings);
        if (!briefingsInitialized) {
          briefingsInitialized = true;
          markStreamReady();
        }
      },
      handleStreamError('briefings')
    );

    const unsubscribeSyntheses = subscribeToSyntheses(
      (nextSyntheses) => {
        if (isCancelled) return;
        setSyntheses(nextSyntheses);
        if (!synthesesInitialized) {
          synthesesInitialized = true;
          markStreamReady();
        }
      },
      handleStreamError('syntheses')
    );

    return () => {
      isCancelled = true;
      unsubscribeBriefings();
      unsubscribeSyntheses();
    };
  }, [user, accessRecord]);

  const openBriefing = (briefingId) => {
    setViewingDateId(briefingId);
    setCurrentView('home');
  };

  const openStory = (storyId) => {
    setViewingStoryId(storyId);
    setCurrentView('story');
  };

  const selectView = (view) => {
    setCurrentView(view);
    if (view === 'home') {
      setViewingDateId(null);
    }
    if (view !== 'story') {
      setViewingStoryId(null);
    }
  };

  const openMenu = () => setIsMenuOpen(true);
  const closeMenu = () => setIsMenuOpen(false);

  const handleImport = async () => {
    if (!isAdmin || !user) {
      setError('Your account does not have permission to modify shared Hermes data.');
      return;
    }

    try {
      setError('');
      setIsImporting(true);

      const sanitizedInput = sanitizeJsonInput(jsonInput);
      const parsed = JSON.parse(sanitizedInput);

      if (parsed.type === 'synthesis') {
        const { valid, errors } = validateSynthesis(parsed);
        if (!valid) throw new Error(`Synthesis import failed: ${errors.join('; ')}`);

        await upsertSynthesis(parsed, user);
        setJsonInput('');
        setCurrentView('synthesis');
        return;
      }

      const archiveBriefings = Array.isArray(parsed.briefings) ? parsed.briefings : [];
      const archiveSyntheses = Array.isArray(parsed.syntheses) ? parsed.syntheses : [];
      const isArchive = Array.isArray(parsed.briefings) || Array.isArray(parsed.syntheses);

      const imports = isArchive ? archiveBriefings : [parsed];

      if (imports.length === 0 && archiveSyntheses.length === 0) {
        throw new Error('No briefings or syntheses found in the provided JSON.');
      }

      imports.forEach((brief, index) => {
        const { valid, errors } = validateDailyBriefing(brief);
        if (!valid) {
          const prefix = isArchive ? `Briefing at index ${index}: ` : '';
          throw new Error(`${prefix}${errors.join('; ')}`);
        }
      });

      archiveSyntheses.forEach((synthesis, index) => {
        const { valid, errors } = validateSynthesis(synthesis);
        if (!valid) {
          throw new Error(`Synthesis at index ${index}: ${errors.join('; ')}`);
        }
      });

      if (imports.length > 0) {
        await upsertBriefings(imports, user);
      }

      if (archiveSyntheses.length > 0) {
        await Promise.all(archiveSyntheses.map((synthesis) => upsertSynthesis(synthesis, user)));
      }

      setJsonInput('');

      if (archiveSyntheses.length > 0 && imports.length === 0) {
        setCurrentView('synthesis');
        return;
      }

      if (isArchive) {
        setViewingDateId(null);
        setCurrentView('home');
        return;
      }

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
    } finally {
      setIsImporting(false);
    }
  };

  const handleImportFileClick = () => {
    if (!isAdmin) return;
    closeMenu();
    fileInputRef.current?.click();
  };

  const handleImportFileSelected = async (event) => {
    const [file] = Array.from(event.target.files || []);
    event.target.value = '';
    if (!file) return;

    try {
      const text = await file.text();
      setJsonInput(text);
      setError('');
      setCurrentView('add');
    } catch {
      setError('Failed to read the selected file.');
      setCurrentView('add');
    }
  };

  const handleExport = () => {
    const timestamp = getExportTimestamp();
    const exportPayload = {
      exportedAt: new Date().toISOString(),
      appVersion: APP_VERSION,
      briefingCount: briefings.length,
      synthesisCount: syntheses.length,
      briefings,
      syntheses
    };

    const readme = [
      'Hermes shared data export',
      `Generated: ${exportPayload.exportedAt}`,
      `App version: ${APP_VERSION}`,
      `Briefing count: ${briefings.length}`,
      `Synthesis count: ${syntheses.length}`,
      '',
      'Files in this export:',
      `- hermes-export-${timestamp}.json: shared briefing and synthesis archive`,
      `- hermes-export-${timestamp}-README.txt: export summary and restore notes`,
      '',
      'Import notes:',
      '- Admin users can import the full hermes-export .json file directly through the app menu to restore shared data.',
      '- Admin users can also import single briefing JSON objects or a single synthesis JSON object directly.'
    ].join('\n');

    downloadFile(
      `hermes-export-${timestamp}.json`,
      JSON.stringify(exportPayload, null, 2),
      'application/json'
    );
    downloadFile(`hermes-export-${timestamp}-README.txt`, readme, 'text/plain;charset=utf-8');
    closeMenu();
  };

  const handleDeleteAll = async () => {
    if (!isAdmin) return;

    closeMenu();
    const shouldDelete = window.confirm(
      `Delete all ${briefings.length} shared briefing${briefings.length === 1 ? '' : 's'} and ${syntheses.length} synthesis overlay${syntheses.length === 1 ? '' : 's'} for every Hermes user?`
    );

    if (!shouldDelete) return;

    try {
      setIsDeleting(true);
      await clearSharedContent();
      setViewingDateId(null);
      setViewingStoryId(null);
      setJsonInput('');
      setError('');
      setQuery('');
      setCurrentView('home');
    } catch (deleteError) {
      setError(deleteError.message || 'Failed to clear shared Hermes data.');
    } finally {
      setIsDeleting(false);
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
      setAuthError(
        signInError.message ||
          'Google sign-in failed. Check Firebase Auth provider settings and try again.'
      );
      setIsSigningIn(false);
    }
  };

  if (!authReady || !accessReady) {
    return (
      <div className="flex min-h-screen items-center justify-center px-6 text-center">
        <div className="space-y-3">
          <div className="text-[10px] font-mono font-bold uppercase tracking-[0.32em] text-cyan-400/80">
            Hermes Access Gate
          </div>
          <div className="text-2xl font-extrabold uppercase tracking-tight stark-gradient-text">
            Authenticating
          </div>
          <div className="text-[13px] text-slate-500">Checking Firebase session and shared access...</div>
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

  if (!contentReady) {
    return (
      <div className="flex min-h-screen items-center justify-center px-6 text-center">
        <div className="space-y-3">
          <div className="text-[10px] font-mono font-bold uppercase tracking-[0.32em] text-cyan-400/80">
            Hermes Data Link
          </div>
          <div className="text-2xl font-extrabold uppercase tracking-tight stark-gradient-text">
            Syncing
          </div>
          <div className="text-[13px] text-slate-500">Loading shared briefings and synthesis overlays...</div>
          {dataError ? <div className="text-[12px] text-red-300">{dataError}</div> : null}
        </div>
      </div>
    );
  }

  const showFloatingMenuButton = !(currentView === 'home' && activeBriefing) && currentView !== 'story';

  return (
    <div className="min-h-screen font-sans text-slate-50 selection:bg-cyan-400/20 selection:text-white">
      <input
        ref={fileInputRef}
        type="file"
        accept=".json,application/json,text/json"
        className="hidden"
        onChange={handleImportFileSelected}
      />

      <AppMenu
        isOpen={isMenuOpen}
        user={user}
        role={accessRecord?.role}
        version={APP_VERSION}
        canImport={isAdmin && !isImporting && !isDeleting}
        canDelete={isAdmin && !isDeleting && !isImporting}
        onClose={closeMenu}
        onSignOut={() => {
          closeMenu();
          signOutUser();
        }}
        onImport={handleImportFileClick}
        onExport={handleExport}
        onDeleteAll={handleDeleteAll}
      />

      {showFloatingMenuButton ? (
        <button
          type="button"
          aria-label="Open menu"
          onClick={openMenu}
          className="fixed left-4 top-4 z-40 flex h-11 w-11 items-center justify-center rounded-2xl border border-cyan-500/20 bg-slate-950/75 text-cyan-300 shadow-[0_14px_32px_rgba(0,0,0,0.35)] backdrop-blur-xl transition-colors hover:border-cyan-400/40 hover:text-cyan-200 md:left-6 md:top-6"
        >
          <Menu size={20} strokeWidth={2.3} />
        </button>
      ) : null}

      <main className={`px-4 pb-32 md:px-6 ${showFloatingMenuButton ? 'pt-16 md:pt-20' : ''}`}>
        {dataError ? (
          <div className="mx-auto mb-5 max-w-2xl rounded-2xl border border-red-500/20 bg-red-950/20 px-4 py-3 text-[12px] text-red-200">
            {dataError}
          </div>
        ) : null}

        {currentView === 'home' && (
          <HomeView
            activeBriefing={activeBriefing}
            latestBriefing={latestBriefing}
            canImport={isAdmin}
            onGoAdd={() => setCurrentView('add')}
            onOpenBriefing={openBriefing}
            onOpenMenu={openMenu}
            onViewThread={openStory}
          />
        )}

        {currentView === 'archive' && (
          <ArchiveView
            briefings={briefings}
            syntheses={syntheses}
            canImport={isAdmin}
            onOpenBriefing={openBriefing}
            onOpenThread={openStory}
            onAdd={() => setCurrentView('add')}
          />
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
            isImporting={isImporting}
            onJsonChange={setJsonInput}
            onImport={handleImport}
            onLoadSample={loadSample}
          />
        )}

        {currentView === 'synthesis' && (
          <SynthesisView syntheses={syntheses} onOpenThread={openStory} />
        )}

        {currentView === 'story' && (
          <StoryView
            storyId={viewingStoryId}
            briefings={briefings}
            syntheses={syntheses}
            onBack={() => selectView('archive')}
            onOpenBriefing={openBriefing}
          />
        )}
      </main>

      <BottomNav currentView={currentView} viewingDateId={viewingDateId} onSelectView={selectView} />
    </div>
  );
}
