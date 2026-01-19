import {Pipe} from '@angular/core';
import {ZaakObject} from '@gu/models';
import {ZaakObjectService} from "@gu/services";

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
  constructor(private zaakObjectService: ZaakObjectService) {
  }

  /**
   * Transforms the object.
   * @param {ZaakObject} zaakObject
   * @return {string}
   */
  transform(zaakObject: ZaakObject): string {
    return this.zaakObjectService.stringifyZaakObject(zaakObject, 5);
  }
}
