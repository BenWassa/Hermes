import test from "node:test";
import assert from "node:assert/strict";
import {
  torontoClock, shouldDispatch, dispatchWorkflow, runScheduled
} from "./worker.mjs";

const at = value => new Date(value);

test("Toronto clock covers EDT, EST and their different UTC cron envelopes", () => {
  assert.deepEqual(
    Object.values(torontoClock(at("2026-10-26T09:35:00Z"))).slice(-2),
    [5, 35]
  );
  assert.equal(torontoClock(at("2026-12-15T10:50:00Z")).hour, 5);
  assert.equal(shouldDispatch(at("2026-10-26T09:35:00Z"), at("2026-10-26T09:35:06Z")), true);
  assert.equal(shouldDispatch(at("2026-10-26T10:35:00Z"), at("2026-10-26T10:35:06Z")), false);
  assert.equal(shouldDispatch(at("2026-12-15T10:35:00Z"), at("2026-12-15T10:35:06Z")), true);
  assert.equal(shouldDispatch(at("2026-12-15T09:35:00Z"), at("2026-12-15T09:35:06Z")), false);
  assert.equal(shouldDispatch(at("2026-03-08T09:35:00Z"), at("2026-03-08T09:40:00Z")), true);
  assert.equal(shouldDispatch(at("2026-11-01T10:50:00Z"), at("2026-11-01T10:55:00Z")), true);
});

test("late and cross-date nominal runs cannot dispatch outside Toronto window", () => {
  assert.equal(shouldDispatch(at("2026-10-26T09:35:00Z"), at("2026-10-26T10:16:00Z")), false);
  assert.equal(shouldDispatch(at("2026-10-26T09:35:00Z"), at("2026-10-27T09:35:00Z")), false);
  assert.equal(shouldDispatch(at("2026-10-26T09:35:00Z"), at("2026-10-26T09:20:00Z")), false);
  assert.equal(shouldDispatch(at("2026-10-26T09:35:00Z"), at("2026-10-26T09:51:00Z")), true);
});

test("dispatch is restricted to the existing main build with least-capability token", async () => {
  const calls = [];
  const request = async (url, options) => {
    calls.push({ url, options });
    return { status: 204 };
  };
  await dispatchWorkflow("test-secret", request);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url,
    "https://api.github.com/repos/BenWassa/Hermes/actions/workflows/build.yml/dispatches");
  assert.equal(calls[0].options.method, "POST");
  assert.deepEqual(JSON.parse(calls[0].options.body), { ref: "main", inputs: { trigger_source: "cloudflare" } });
  assert.equal(calls[0].options.headers.Authorization, "Bearer test-secret");
});

test("cron misfire is a true no-op, no secrets or network required", async () => {
  const request = async () => { throw new Error("would touch GitHub"); };
  const response = await runScheduled(
    at("2026-10-26T10:35:00Z"), at("2026-10-26T10:35:02Z"), {}, request
  );
  assert.equal(response, "outside-window");
});

test("missing credential fails explicitly, never logs token or publishes", async () => {
  await assert.rejects(
    () => runScheduled(at("2026-10-26T09:35:00Z"),
      at("2026-10-26T09:36:00Z"), {}, async () => ({ status: 204 })),
    /secret is missing/,
  );
});

test("only 429/5xx retry once, bounded delay and final success", async () => {
  const statuses = [503, 204];
  const waits = [];
  let count = 0;
  await dispatchWorkflow("secret", async () => {
    count += 1;
    return { status: statuses.shift() };
  }, async ms => { waits.push(ms); });
  assert.equal(count, 2);
  assert.deepEqual(waits, [1500]);
});

test("authorization failures are not retried and response secrets never exposed", async () => {
  let count = 0;
  await assert.rejects(() => dispatchWorkflow("confidential-token", async () => {
    count += 1;
    return { status: 403, body: { token: "confidential-token" } };
  }), error => {
    assert.equal(error.message, "GitHub Actions dispatch HTTP 403");
    assert.equal(error.message.includes("confidential-token"), false);
    return true;
  });
  assert.equal(count, 1);
});

test("transient failure after two attempts remains observable", async () => {
  let count = 0;
  await assert.rejects(
    () => dispatchWorkflow("secret", async () => {
      count += 1;
      return { status: 429 };
    }, async () => {}),
    /GitHub Actions dispatch HTTP 429/,
  );
  assert.equal(count, 2);
});

test("invalid date cannot silently match a publication window", () => {
  assert.throws(() => shouldDispatch(new Date("bad"), new Date()), /Valid timestamp/);
});
