/**
 * Returns the substituted value in SUPPORTED_ENV_VARS for envvar, or defaultValue.
 * @param {string} envVar
 * @param {*} defaultValue
 * @return {*}
 */
export const getEnv = (envVar: string, defaultValue: any): any => {
  // In order to prevent unwanted code replacements, only occurrences starting with "$" are replaced.
  // Therefore, code fragments calling getEnv should not include the dollar sign (to keep the code intact).
  if(String(envVar).startsWith('$')) {
    throw new Error(`Value for "value" (${envVar}) should not start with "$"`);
  }

  const _window = (window) ? window : {};
  const env = _window['env'] || {};
  const value = env[envVar];
  return (String(value).startsWith('$') || value === undefined) ? defaultValue : value;
}
