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
  name: 'objectType'
})
export class AuthProfilesPipe {

  /**
   * Transforms object type to human readible text
   * @param objectType
   * @returns {string}
   */
  transform(objectType): string {
    switch (objectType) {
      case "zaak":
        return "Zaak";
      case "document":
        return "Document";
      case "search_report":
        return "Rapportage";
    }
  }
}
