/**
 * Dashboard-only request scheduling (presentation layer, no API changes).
 *
 * The home dashboard renders ~8 widgets that each call an existing client.
 * Firing them all at once makes the local TinyDB-backed auth lookup race
 * (concurrent reads of the same JSON file), which surfaces as 500s or a 401
 * that logs the user out. Running dashboard requests one at a time and sharing
 * identical requests between widgets avoids that without touching the API.
 */

let tail: Promise<unknown> = Promise.resolve();

/** Run `task` after every previously enqueued dashboard request has settled. */
export function enqueue<T>(task: () => Promise<T>): Promise<T> {
  const run = tail.then(task, task);
  tail = run.catch(() => undefined);
  return run;
}

const SHARE_WINDOW_MS = 3000;
const shared = new Map<string, { startedAt: number; promise: Promise<unknown> }>();

/** Enqueue `task`, reusing an identical request (same key) started in the last few seconds. */
export function sharedRequest<T>(key: string, task: () => Promise<T>): Promise<T> {
  const now = Date.now();
  const existing = shared.get(key);
  if (existing && now - existing.startedAt < SHARE_WINDOW_MS) {
    return existing.promise as Promise<T>;
  }
  const promise = enqueue(task);
  shared.set(key, { startedAt: now, promise });
  promise.catch(() => shared.delete(key));
  return promise;
}
