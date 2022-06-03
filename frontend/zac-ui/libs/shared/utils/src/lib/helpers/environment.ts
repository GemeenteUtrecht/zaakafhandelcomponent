// A mapping between the name of an environment variable, and its replacement target (to be substituted by envsubst).
const SUPPORTED_ENV_VARS = {
  "ALFRESCO_AUTH_URL": "$ALFRESCO_AUTH_URL",
  "ALFRESCO_PREVIEW_URL": "$ALFRESCO_PREVIEW_URL",
  "ALFRESCO_DOCUMENTS_URL": "$ALFRESCO_DOCUMENTS_URL",
  "FORMS_URL": "$FORMS_URL",
}

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

  const value = SUPPORTED_ENV_VARS[envVar];
  return (String(value).startsWith('$')) ? defaultValue : value;
}
