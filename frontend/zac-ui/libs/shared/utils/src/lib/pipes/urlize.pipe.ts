import { Pipe, PipeTransform } from '@angular/core';
import {DomSanitizer, SafeHtml} from '@angular/platform-browser';


/**
 * Formats a string to HTML with clickable links for every matched link.
 * Usage:
 *   value | urlize
 * Example:
 *   <div [innerHTML]="field.value|urlize"></div>
 *   <div [innerHTML]="field.value|urlize:'_blank'"></div>
 *
 * Argument 1 may be set to value of target attribute.
*/
@Pipe({
  name: 'urlize',
})
export class UrlizePipe implements PipeTransform {
  constructor(private domSanitizer: DomSanitizer) {}

  transform(unsafeValue: string, target='_self'): SafeHtml {
    const safeValue = new DOMParser().parseFromString(unsafeValue, 'text/html').body.textContent;
    const regExp = new RegExp("(?:(?:https?://)|(?:www))[^\s]+", "gi")
    const html = safeValue.replace(regExp, (match) => {
      const href = (match.match('http')) ? match : `http://${match}`;
      return `<a href="${href}" target="${target}">${match}</a>`;
    });
    return this.domSanitizer.bypassSecurityTrustHtml(html);
  }
}
