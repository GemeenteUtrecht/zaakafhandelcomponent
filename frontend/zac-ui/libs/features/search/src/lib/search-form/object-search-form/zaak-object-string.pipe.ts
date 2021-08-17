import {Pipe} from "@angular/core";
import {ZaakObject} from './zaak-object';

/**
 * Turns a ZaakObject into a human-readable string.
 * Usage:
 *   value | zaakObjectString
 * Example:
 *   {{ zaakObject | zaakObjectString }}
 *   formats to: Adres: Utrechtsestraat 41, Status: Laadpaal in ontwikkeling, Type: Laadpaal
*/
@Pipe({
  name: 'zaakObjectString'
})
export class ZaakObjectStringPipe {
  /**
   * Transforms the object.
   * @param {ZaakObject} zaakObject
   * @return {string}
   */
  transform(zaakObject: ZaakObject): string {
    return Object.entries(zaakObject.record.data)
      .filter(([key, value]) => ['objectid'].indexOf(key.toLowerCase()) === -1)
      .map(([key, value]) => `${key[0].toUpperCase() + key.slice(1)}: ${value}`)
      .sort()
      .join(', ');
  }
}
