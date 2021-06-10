/**
 * Returns whether the current environment is assumed to be a development environment.
 * A development environment is assumed when the current window's location matches 'test' or 'localhost'.
 * @TODO: Use a more solid check.
 * @return {Boolean}
 */
export const isDevelopmentEnvironment = () => {
  const url = String(window.location);
  return Boolean(url.match('test') || url.match('localhost'));
}
