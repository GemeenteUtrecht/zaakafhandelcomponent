/**
 * Returns whether the current environment is assumed to be a development environment.
 * A development environment is assumed when the current window's location matches 'test' or 'localhost'.
 * @TODO: Use a more solid check.
 * @return {Boolean}
 */
export const isTestEnvironment = () => {
  const url = String(window.location);
  return Boolean(url.match('ont') || url.match('localhost'));
}
