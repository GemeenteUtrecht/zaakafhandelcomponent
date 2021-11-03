import {Observable} from "rxjs";
import {getCache, setCache, getIsCached, setIsCached, getCacheFailed, setCacheFailed, clearCache} from './cache';

/**
 * Method decorator which caches a method returning an observable.
 * Observable is replaced with a new observable for a cached value.
 * This reduces API load on a service.
 *
 * @param {string} [identifierKey] Key used for identification, if omitted <target.constructor.name>.<propertyKey> will
 * be used (e.g. 'MyService.getDetails').
 * @param {number} maxCacheAgeInSeconds Max cache age.
 * @return Function
 */
export function CachedObservableMethod(identifierKey = '', maxCacheAgeInSeconds = 10,) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    // Check if we have a window object (required for storing cache).
    if (!window) {
      return;
    }

    const originalFn = descriptor.value;
    const generatedKey = `${target.constructor.name}.${propertyKey}`;
    const cacheKey = identifierKey || generatedKey;

    /**
     * The replacement function.
     * This returns an observable which results in the output of the wrapped method.
     * Might not work with observers outputting multiple values.
     * @param {...*} args
     */
    const replacementFn = function (...args) {
      // Subscribe to original fn/observable and store data.
      if (!getIsCached(cacheKey, args, maxCacheAgeInSeconds)) {
        originalFn.call(this, ...args).subscribe(
          (data) => setCache(cacheKey, args, data),
          (error) => {
            setCache(cacheKey, args, error),
            setCacheFailed(cacheKey, args, true);
          },
        );

        // Mark as cached (even through cache is not YET ready).
        // This makes sure the mock observable gets returned awaiting the initial data (hitting externals once).
        setIsCached(cacheKey, args, true);
      }

      // Return a mock observable which returns the cached value (once available).
      return new Observable((subscriber => {
        const tick = () => {
          const cache = getCache(cacheKey, args);

          if (cache) {
            if (getCacheFailed(cacheKey, args)) {
              subscriber.error(cache);
            } else {
              subscriber.next(cache);
            }
            subscriber.complete();
            return;
          }

          setTimeout(tick);
        };
        tick();
      }));
    };

    descriptor.value = replacementFn;
  };
}

/**
 * Method decorator which, on a decorated method call clears the cache associated with identifierKey.
 *
 * @param {string} [identifierKey] Key used for identification.
 * @return Function
 */
export function ClearCacheOnMethodCall(identifierKey = '') {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalFn = descriptor.value;

    /**
     * The replacement function.
     * This acts as a proxy to the original function, but clearing the cache associated with identifierKey beforehand.
     * @param {...*} args
     */
    const replacementFn = function (...args) {
      clearCache(identifierKey);
      return originalFn.call(this, ...args);
    }

    descriptor.value = replacementFn;
  }
}
