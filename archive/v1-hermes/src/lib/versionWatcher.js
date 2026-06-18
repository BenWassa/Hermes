const VERSION_ENDPOINT = '/version.json';
const CHECK_INTERVAL_MS = 5 * 60 * 1000;
const RELOAD_SESSION_KEY = 'hermes:reloaded-build-id';

async function fetchLatestBuildId() {
  const response = await fetch(`${VERSION_ENDPOINT}?t=${Date.now()}`, {
    cache: 'no-store',
    headers: {
      'Cache-Control': 'no-cache'
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch version metadata: ${response.status}`);
  }

  const payload = await response.json();
  return typeof payload?.buildId === 'string' ? payload.buildId : null;
}

export function startVersionWatcher() {
  if (import.meta.env.DEV || typeof window === 'undefined') {
    return () => {};
  }

  let disposed = false;

  const checkForNewBuild = async () => {
    if (disposed) return;

    try {
      const latestBuildId = await fetchLatestBuildId();

      if (!latestBuildId || latestBuildId === __APP_BUILD_ID__) {
        window.sessionStorage.removeItem(RELOAD_SESSION_KEY);
        return;
      }

      if (window.sessionStorage.getItem(RELOAD_SESSION_KEY) === latestBuildId) {
        return;
      }

      window.sessionStorage.setItem(RELOAD_SESSION_KEY, latestBuildId);
      window.location.reload();
    } catch {
      // Ignore transient network/CDN failures and try again later.
    }
  };

  const handleVisibilityChange = () => {
    if (document.visibilityState === 'visible') {
      void checkForNewBuild();
    }
  };

  const handleFocus = () => {
    void checkForNewBuild();
  };

  window.addEventListener('visibilitychange', handleVisibilityChange);
  window.addEventListener('focus', handleFocus);

  const intervalId = window.setInterval(() => {
    void checkForNewBuild();
  }, CHECK_INTERVAL_MS);

  void checkForNewBuild();

  return () => {
    disposed = true;
    window.clearInterval(intervalId);
    window.removeEventListener('visibilitychange', handleVisibilityChange);
    window.removeEventListener('focus', handleFocus);
  };
}
