//
// Public (cache) API.
//

/**
 * Returns the cache.
 * @param baseKey {string} The base key for the cached target, used together with args to create a unique identifier.
 * @param args {*[]} Arguments passed to the cached method.
 * @return {*|null}
 */
export const getCache = (baseKey: string, args: any[]): any => {
  if (getIsCached(baseKey, args)) {
    return _getCacheBackend().getValue(_getCacheKey(baseKey, args)) || null;
  }
  return null;
}

/**
 * Sets the cache.
 * @param baseKey {string} The base key for the cached target, used together with args to create a unique identifier.
 * @param args {*[]} Arguments passed to the cached method.
 * @param {*} data
 */
export const setCache = (baseKey: string, args: any[], data: any): void => {
  _getCacheBackend().setValue(_getCacheKey(baseKey, args), data)
  setIsCached(baseKey, args, true);
}

/**
 * Clears all cache items associated with baseKey.
 * @param baseKey {string} The base key for the cached target.
 */
export const clearCache = (baseKey: string): void => {
  _getCacheBackend().clearValues(baseKey);
}

/**
 * Returns whether the cache is active.
 * @param baseKey {string} The base key for the cached target, used together with args to create a unique identifier.
 * @param args {*[]} Arguments passed to the cached method.
 * @param {number} [maxCacheAgeInSeconds=10] Maximum cache age.
 */
export const getIsCached = (baseKey: string, args: any[], maxCacheAgeInSeconds=10): boolean => {
  if (!_getCacheBackend().getTimestamp(_getCacheKey(baseKey, args))) {
    return false;
  }

  const currentTimestamp = Math.round(+new Date() / 1000);
  const cacheTimestamp = _getCacheBackend().getTimestamp(_getCacheKey(baseKey, args));
  return currentTimestamp - cacheTimestamp < maxCacheAgeInSeconds;
}

/**
 * Sets whether the cache is active.
 * @param baseKey {string} The base key for the cached target, used together with args to create a unique identifier.
 * @param args {*[]} Arguments passed to the cached method.
 * @param {boolean} isCached
 */
export const setIsCached = (baseKey: string, args: any[], isCached: Boolean): void => {
  if (isCached) {
    const timestamp = Math.round(+new Date() / 1000);
    _getCacheBackend().setTimestamp(_getCacheKey(baseKey, args), timestamp);
    return;
  }
  _getCacheBackend().setTimestamp(_getCacheKey(baseKey, args), null);
}

/**
 * Returns whether tthe attempt of caching resulted in a failure.
 * @param baseKey {string} The base key for the cached target, used together with args to create a unique identifier.
 * @param args {*[]} Arguments passed to the cached method.
 * @return {boolean}
 */
export const getCacheFailed = (baseKey: string, args: any[]): boolean => {
  return _getCacheBackend().getFailed(_getCacheKey(baseKey, args));
}

/**
 * Sets whether the attempt of caching resulted in a failure.
 * @param baseKey {string} The base key for the cached target, used together with args to create a unique identifier.
 * @param args {*[]} Arguments passed to the cached method.
 * @param {boolean} cacheFailed
 */
export const setCacheFailed = (baseKey: string, args: any[], cacheFailed: boolean): void => {
  _getCacheBackend().setFailed(_getCacheKey(baseKey, args), cacheFailed)
}


//
// Private (cache) API.
//

/**
 * @param {string} baseKey
 * @param {*[]} args
 * @return {string} The base key for the cached target, based on baseKey and args.
 */
const _getCacheKey = (baseKey: string, args: any[]): string => {
  return `${baseKey.replace(/_/g, '')}__${args.map((arg) => String(arg).replace(/_/g, ''))
    .join('_')}__`;
}

interface CacheBackend {
  getValue: (key: string) => any;
  setValue: (key: string, value: any) => void;
  getFailed: (key: string) => boolean;
  setFailed: (key: string, value: boolean) => void;
  clearValues: (key: string) => void;

  getTimestamp: (key: string) => number;
  setTimestamp: (key: string, timestamp: number | null) => void;
}

interface WindowCacheBackend extends CacheBackend {
  entries: Object
}

/**
 * Returns the cache backend (storing results on window.__cache__.
 * @return {CacheBackend}
 */
const _getCacheBackend = (): CacheBackend => {
  const backend: WindowCacheBackend = {
    entries: {},

    getValue: (key: string): any => window['__cache__'].entries[`${key}value`],
    setValue: (key: string, value: any): void => window['__cache__'].entries[`${key}value`] = value,

    getFailed: (key: string): any => window['__cache__'].entries[`${key}failed`],
    setFailed: (key: string, failed: boolean): boolean => window['__cache__'].entries[`${key}failed`] = failed,

    clearValues: (key: string) => Object.keys(window['__cache__'].entries)
      .filter((cachedKey) => cachedKey.startsWith(key))
      .forEach((cachedKey) => delete window['__cache__'].entries[cachedKey]),

    getTimestamp: (key: string): number => window['__cache__'].entries[`${key}timestamp`],
    setTimestamp: (key: string, timestamp: number | null) => window['__cache__'].entries[`${key}timestamp`] = timestamp,
  }

  if (!window['__cache__']) {
    window['__cache__'] = backend;
  }

  return window['__cache__'];
};
