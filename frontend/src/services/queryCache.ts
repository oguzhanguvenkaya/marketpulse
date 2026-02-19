type CacheEntry<T> = {
  value: T;
  expiresAt: number;
};

type FetchOptions = {
  ttlMs?: number;
  forceRefresh?: boolean;
  skipDedupe?: boolean;
};

const DEFAULT_TTL_MS = Number(import.meta.env.VITE_QUERY_CACHE_TTL_MS ?? 45000);

const cacheStore = new Map<string, CacheEntry<unknown>>();
const inFlightStore = new Map<string, Promise<unknown>>();

function stableStringify(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(',')}]`;
  }

  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
      .filter(([, v]) => v !== undefined)
      .sort(([a], [b]) => a.localeCompare(b));
    return `{${entries.map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`).join(',')}}`;
  }

  return JSON.stringify(value);
}

function shouldLog() {
  return import.meta.env.DEV;
}

function logEvent(message: string) {
  if (shouldLog()) {
    console.debug(`[query-cache] ${message}`);
  }
}

export function buildCacheKey(namespace: string, params?: Record<string, unknown>): string {
  if (!params) {
    return namespace;
  }
  return `${namespace}:${stableStringify(params)}`;
}

export async function getCachedOrFetch<T>(
  key: string,
  fetcher: () => Promise<T>,
  options: FetchOptions = {},
): Promise<T> {
  const forceRefresh = options.forceRefresh === true;
  const ttlMs = options.ttlMs ?? DEFAULT_TTL_MS;
  const skipDedupe = options.skipDedupe === true;
  const now = Date.now();

  if (forceRefresh) {
    cacheStore.delete(key);
  } else {
    const cached = cacheStore.get(key);
    if (cached && cached.expiresAt > now) {
      logEvent(`hit key=${key}`);
      return cached.value as T;
    }
  }

  if (!skipDedupe) {
    const existingPromise = inFlightStore.get(key) as Promise<T> | undefined;
    if (existingPromise) {
      logEvent(`dedupe key=${key}`);
      return existingPromise;
    }
  } else {
    logEvent(`miss key=${key} (skip dedupe)`);
    const directValue = await fetcher();
    cacheStore.set(key, { value: directValue, expiresAt: Date.now() + ttlMs });
    return directValue;
  }

  logEvent(`miss key=${key}`);
  const promise = fetcher()
    .then((value) => {
      cacheStore.set(key, { value, expiresAt: Date.now() + ttlMs });
      return value;
    })
    .finally(() => {
      inFlightStore.delete(key);
    });

  inFlightStore.set(key, promise);
  return promise;
}

export function invalidateCacheByPrefix(prefix: string): void {
  for (const key of cacheStore.keys()) {
    if (key.startsWith(prefix)) {
      cacheStore.delete(key);
    }
  }
  for (const key of inFlightStore.keys()) {
    if (key.startsWith(prefix)) {
      inFlightStore.delete(key);
    }
  }
  logEvent(`invalidate prefix=${prefix}`);
}

export function invalidateCacheKeys(keys: string[]): void {
  for (const key of keys) {
    cacheStore.delete(key);
    inFlightStore.delete(key);
    logEvent(`invalidate key=${key}`);
  }
}

export function clearQueryCache(): void {
  cacheStore.clear();
  inFlightStore.clear();
  logEvent('clear all');
}
