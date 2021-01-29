// source https://gitlab.com/nl-design-system/nl-design-system/-/blob/master/src/core/utils.ts

/**
 * Checks if a certain key is pressed, converts keynames to browser specific names.
 * For instance, the 'ArrowDown' key in Chrome is called 'ArrowDown', in IE it's called 'Down'
 * @param event The original event
 * @param key The name of the key, as specified in the docs (https://developer.mozilla.org/nl/docs/Web/API/KeyboardEvent/key/Key_Values)
 * @constructor
 */
export const isKeyPressed = (event: KeyboardEvent, key: string): boolean => {
  const ambiguous: any = {
    ' ': ['Space', 'Spacebar', 'Space Bar'],
    'ArrowDown': ['Down'],
    'ArrowLeft': ['Left'],
    'ArrowRight': ['Right'],
    'ArrowUp': ['Up'],
    'ContextMenu': ['Apps'],
    'CrSel': ['Crsel'],
    'Delete': ['Del'],
    'Escape': ['Esc'],
    'ExSel': ['Exsel']
  };

  if (event.key === key) {
    return true;
  }

  if (ambiguous.hasOwnProperty(key)) {
    return ambiguous[key].reduce(
      (pressed: boolean, alt: string) => {
        pressed = pressed || event.key === alt;
        return pressed;
      },
      false);
  }

  return false;
}
