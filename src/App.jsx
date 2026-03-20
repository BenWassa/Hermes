import { useEffect, useRef, useState } from 'react';
import { Menu } from 'lucide-react';
import { BottomNav } from './components/BottomNav';
import { AppMenu } from './components/AppMenu';
import { SAMPLE_BRIEFING } from './data/sampleBriefing';
import {
  clearSharedContent,
  deleteBriefing,
  getAccessRecord,
  signInWithGoogle,
  signOutUser,
  subscribeToAmplifiers,
  subscribeToAuthState,
  subscribeToBriefings,
  subscribeToSyntheses,
  upsertAmplifier,
  upsertBriefings,
  upsertSynthesis
} from './lib/firebase';
import { getTodayId } from './utils/date';
import { sanitizeJsonInput, validateAmplifier, validateDailyBriefing, validateSynthesis } from './utils/json';
import { AddBriefingView } from './views/AddBriefingView';
import { ArchiveView } from './views/ArchiveView';
import { HomeView } from './views/HomeView';
import { ImportFlowView } from './views/ImportFlowView';
import { OnboardingView } from './views/OnboardingView';
import { SearchView } from './views/SearchView';
import { StoryView } from './views/StoryView';
import { WorkflowView } from './views/WorkflowView';
import packageMetadata from '../package.json';

const APP_VERSION = packageMetadata.version;

function formatFirebaseError(error, fallbackMessage) {
  if (!error) return fallbackMessage;

  const message = error.message || fallbackMessage;

  if (error.code === 'permission-denied') {
    return 'Hermes could not read shared Firestore data. Your signed-in account may be missing an active access record, or the deployed Firestore rules may be out of date.';
  }

  return message;
}

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
  const [amplifiers, setAmplifiers] = useState([]);
  const [importPhase, setImportPhase] = useState(null); // null | 'step2' | 'loading'
  const [currentView, setCurrentView] = useState('home');
  const [viewingDateId, setViewingDateId] = useState(null);
  const [viewingStoryId, setViewingStoryId] = useState(null);
  const [jsonInput, setJsonInput] = useState('');
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const fileInputRef = useRef(null);

  const isAdmin = accessRecord?.role === 'admin';
  const todayId = getTodayId();
  const todayBriefing = briefings.find((briefing) => briefing.id === todayId);
  const todayAmplifier = amplifiers.find((a) => a.briefing_id === todayId);

  const activeBriefing = viewingDateId
    ? briefings.find((briefing) => briefing.id === viewingDateId)
    : todayBriefing;
  const activeAmplifier = viewingDateId
    ? amplifiers.find((a) => a.briefing_id === viewingDateId)
    : todayAmplifier;
  const latestBriefing = briefings.length > 0 ? briefings[0] : null;


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
        setAmplifiers([]);
        setImportPhase(null);
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
        console.error('Hermes access verification failed', {
          code: accessError?.code,
          message: accessError?.message,
          uid: nextUser?.uid
        });
        setUser(null);
        setAccessRecord(null);
        setAccessReady(true);
        setAuthError(formatFirebaseError(accessError, 'Failed to verify Hermes access.'));
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
    let pendingStreams = 3;
    let briefingsInitialized = false;
    let synthesesInitialized = false;
    let amplifiersInitialized = false;

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
      console.error(`Hermes ${streamLabel} stream failed`, {
        code: streamError?.code,
        message: streamError?.message,
        uid: user?.uid
      });
      setDataError(
        formatFirebaseError(streamError, `Failed to load shared ${streamLabel}.`)
      );
      if (streamLabel === 'briefings' && !briefingsInitialized) {
        briefingsInitialized = true;
        markStreamReady();
      }
      if (streamLabel === 'syntheses' && !synthesesInitialized) {
        synthesesInitialized = true;
        markStreamReady();
      }
      if (streamLabel === 'amplifiers' && !amplifiersInitialized) {
        amplifiersInitialized = true;
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

    const unsubscribeAmplifiers = subscribeToAmplifiers(
      (nextAmplifiers) => {
        if (isCancelled) return;
        setAmplifiers(nextAmplifiers);
        if (!amplifiersInitialized) {
          amplifiersInitialized = true;
          markStreamReady();
        }
      },
      handleStreamError('amplifiers')
    );

    return () => {
      isCancelled = true;
      unsubscribeBriefings();
      unsubscribeSyntheses();
      unsubscribeAmplifiers();
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
    setCurrentView(view === 'synthesis' ? 'archive' : view);
    setImportPhase(null);
    if (view === 'home') {
      setViewingDateId(null);
    }
    if (view !== 'story') {
      setViewingStoryId(null);
    }
  };

  const openMenu = () => setIsMenuOpen(true);
  const closeMenu = () => setIsMenuOpen(false);

  const handleImport = async (inputOverride) => {
    if (!isAdmin || !user) {
      setError('Your account does not have permission to modify shared Hermes data.');
      return;
    }

    try {
      setError('');
      setIsImporting(true);

      const sanitizedInput = sanitizeJsonInput(inputOverride ?? jsonInput);
      const parsed = JSON.parse(sanitizedInput);

      if (parsed.type === 'amplifier') {
        const { valid, errors } = validateAmplifier(parsed);
        if (!valid) throw new Error(`Amplifier import failed: ${errors.join('; ')}`);

        await upsertAmplifier(parsed, user);
        setJsonInput('');
        setViewingDateId(null);
        setImportPhase('loading');
        setTimeout(() => {
          setImportPhase(null);
          setCurrentView('home');
        }, 1800);
        return;
      }

      if (parsed.type === 'synthesis') {
        const { valid, errors } = validateSynthesis(parsed);
        if (!valid) throw new Error(`Synthesis import failed: ${errors.join('; ')}`);

        await upsertSynthesis(parsed, user);
        setJsonInput('');
        setViewingDateId(null);
        setCurrentView('archive');
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
        setViewingDateId(null);
        setCurrentView('archive');
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
        setImportPhase('step2');
      } else {
        setViewingDateId(parsed.id);
        setCurrentView('archive');
      }
    } catch (importError) {
      console.error('Hermes import failed', {
        code: importError?.code,
        message: importError?.message,
        uid: user?.uid
      });
      setError(
        formatFirebaseError(
          importError,
          'Invalid JSON syntax. Check for malformed structure or unsupported pasted formatting.'
        )
      );
    } finally {
      setIsImporting(false);
    }
  };

  const handleClipboardImport = async () => {
    if (!isAdmin || !user) return;
    try {
      const text = await navigator.clipboard.readText();
      setJsonInput(text);
      await handleImport(text);
    } catch {
      setError('Could not read clipboard. Copy the JSON output and try again.');
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
      `Additional overlay count: ${syntheses.length}`,
      '',
      'Files in this export:',
      `- hermes-export-${timestamp}.json: shared Hermes archive export`,
      `- hermes-export-${timestamp}-README.txt: export summary and restore notes`,
      '',
      'Import notes:',
      '- Admin users can import the full hermes-export .json file directly through the app menu to restore shared data.',
      '- Admin users can also import individual Hermes JSON objects directly.'
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
      `Delete all shared Hermes data for every approved user? This includes ${briefings.length} briefing${briefings.length === 1 ? '' : 's'} and ${syntheses.length} hidden overlay record${syntheses.length === 1 ? '' : 's'}.`
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
      console.error('Hermes clear shared content failed', {
        code: deleteError?.code,
        message: deleteError?.message,
        uid: user?.uid
      });
      setError(formatFirebaseError(deleteError, 'Failed to clear shared Hermes data.'));
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteBriefing = async (briefing) => {
    if (!isAdmin) return;

    const shouldDelete = window.confirm(
      `Delete shared briefing ${briefing.date || briefing.id} for every Hermes user?`
    );

    if (!shouldDelete) return;

    try {
      setIsDeleting(true);
      setError('');
      await deleteBriefing(briefing.id);

      if (viewingDateId === briefing.id) {
        setViewingDateId(null);
        setCurrentView('archive');
      }
    } catch (deleteError) {
      console.error('Hermes delete briefing failed', {
        code: deleteError?.code,
        message: deleteError?.message,
        uid: user?.uid,
        briefingId: briefing?.id
      });
      setError(formatFirebaseError(deleteError, `Failed to delete briefing ${briefing.id}.`));
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
      console.error('Hermes Google sign-in failed', {
        code: signInError?.code,
        message: signInError?.message
      });
      setAuthError(
        formatFirebaseError(
          signInError,
          'Google sign-in failed. Check Firebase Auth provider settings and try again.'
        )
      );
      setIsSigningIn(false);
    }
  };

  if (!authReady || !accessReady) {
    return (
      <div className="flex min-h-app items-center justify-center px-6 text-center">
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
      <div className="min-h-app font-sans text-slate-50 selection:bg-cyan-400/20 selection:text-white">
        <OnboardingView isSigningIn={isSigningIn} error={authError} onSignIn={handleGoogleSignIn} />
      </div>
    );
  }

  if (!contentReady) {
    return (
      <div className="flex min-h-app items-center justify-center px-6 text-center">
        <div className="space-y-3">
          <div className="text-[10px] font-mono font-bold uppercase tracking-[0.32em] text-cyan-400/80">
            Hermes Data Link
          </div>
          <div className="text-2xl font-extrabold uppercase tracking-tight stark-gradient-text">
            Syncing
          </div>
          <div className="text-[13px] text-slate-500">Loading shared Hermes archive...</div>
          {dataError ? <div className="text-[12px] text-red-300">{dataError}</div> : null}
        </div>
      </div>
    );
  }

  const showFloatingMenuButton = !(currentView === 'home' && activeBriefing) && currentView !== 'story';

  return (
    <div className="min-h-app font-sans text-slate-50 selection:bg-cyan-400/20 selection:text-white">
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

        {currentView === 'home' && isAdmin && (!todayBriefing || importPhase === 'step2' || importPhase === 'loading') && (
          <ImportFlowView
            step={!todayBriefing ? 1 : 2}
            isLoading={importPhase === 'loading'}
            error={error}
            isImporting={isImporting}
            onClipboardPaste={handleClipboardImport}
            onGoToWorkflow={() => setCurrentView('workflow')}
          />
        )}

        {currentView === 'home' && (!isAdmin || (todayBriefing && !importPhase)) && (
          <HomeView
            activeBriefing={activeBriefing}
            amplifier={activeAmplifier}
            latestBriefing={latestBriefing}
            canImport={isAdmin}
            onGoAdd={() => setCurrentView('add')}
            onOpenBriefing={openBriefing}
            onOpenMenu={openMenu}
            onViewThread={openStory}
          />
        )}

        {currentView === 'workflow' && isAdmin && (
          <WorkflowView
            todaysBriefing={todayBriefing}
            onGoToImport={() => setCurrentView('add')}
          />
        )}

        {currentView === 'archive' && (
          <ArchiveView
            briefings={briefings}
            canImport={isAdmin}
            canDelete={isAdmin && !isDeleting}
            onOpenBriefing={openBriefing}
            onOpenThread={openStory}
            onAdd={() => setCurrentView('add')}
            onDeleteBriefing={handleDeleteBriefing}
          />
        )}

        {currentView === 'search' && (
          <SearchView
            briefings={briefings}
            query={query}
            onQueryChange={setQuery}
            onOpenBriefing={openBriefing}
            onOpenThread={openStory}
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

{currentView === 'story' && (
          <StoryView
            storyId={viewingStoryId}
            briefings={briefings}
            onBack={() => selectView('archive')}
            onOpenBriefing={openBriefing}
          />
        )}
      </main>

      <BottomNav currentView={currentView} viewingDateId={viewingDateId} onSelectView={selectView} />
    </div>
  );
}
