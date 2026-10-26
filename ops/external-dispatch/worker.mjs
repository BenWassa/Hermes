/**
 * Independent UTC Cron -> existing GitHub Actions Daily workflow_dispatch.
 *
 * No HTTP handler, no persisted user data, no provider/model calls. All edition
 * identity, Toronto >=05:00 gate, publication and notification semantics remain
 * wholly inside .github/workflows/build.yml on main.
 */
const WORKFLOW_URL =
  "https://api.github.com/repos/BenWassa/Hermes/actions/workflows/build.yml/dispatches";
const TORONTO_TIME = new Intl.DateTimeFormat("en-GB", {
  timeZone: "America/Toronto",
  year: "numeric", month: "2-digit", day: "2-digit",
  hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});

export function torontoClock(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
    throw new TypeError("Valid timestamp required");
  }
  const parts = Object.fromEntries(
    TORONTO_TIME.formatToParts(date)
      .filter(part => part.type !== "literal")
      .map(part => [part.type, Number(part.value)])
  );
  return parts;
}

/**
 * 09:35/09:50 UTC map to 05:35/05:50 EDT; 10:35/10:50 UTC
 * map to 05:35/05:50 EST. The *other* pair is always a no-op.
 * Check scheduled instant and actual execution time to reject stale deliveries.
 */
export function shouldDispatch(scheduled, actual) {
  const target = torontoClock(scheduled);
  const now = torontoClock(actual);
  if (target.year !== now.year || target.month !== now.month || target.day !== now.day) {
    return false;
  }
  if (target.hour !== 5 || ![35, 50].includes(target.minute)) return false;
  const actualMinutes = now.hour * 60 + now.minute;
  return actualMinutes >= 5 * 60 + 30 && actualMinutes <= 6 * 60 + 15;
}

export async function dispatchWorkflow(token, request = fetch, pause = async ms => {
  await new Promise(resolve => setTimeout(resolve, ms));
}) {
  if (typeof token !== "string" || !token.trim()) {
    throw new Error("GitHub Actions dispatch secret is missing");
  }
  for (let attempt = 1; attempt <= 2; attempt += 1) {
    // No dynamic repo/ref input: token may only launch the existing main build.
    const response = await request(WORKFLOW_URL, {
      method: "POST",
      headers: {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "hermes-independent-morning-dispatch",
      },
      body: JSON.stringify({ ref: "main", inputs: { trigger_source: "cloudflare" } }),
    });
    if (response.status === 204 || response.status === 200) return;
    const retryable = response.status === 429 || response.status >= 500;
    if (!retryable || attempt === 2) {
      // Never log response bodies (may include account/path details), headers
      // or tokens; Cloudflare marks failed scheduled runs in its events.
      throw new Error("GitHub Actions dispatch HTTP " + response.status);
    }
    await pause(1_500);
  }
}

export async function runScheduled(scheduled, actual, env, request = fetch, pause) {
  if (!shouldDispatch(scheduled, actual)) return "outside-window";
  await dispatchWorkflow(env?.GITHUB_DISPATCH_TOKEN, request, pause);
  console.log("GitHub Daily workflow_dispatch accepted");
  return "dispatched";
}

export default {
  async scheduled(controller, env) {
    // Cloudflare's scheduledTime is the nominal UTC instant. Use *actual*
    // current time as the bounded execution-window check as well.
    return runScheduled(new Date(controller.scheduledTime), new Date(), env);
  },
};
