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

  transform(value: string, target='_self'): SafeHtml {
    const regExp = new RegExp("(?:(?:https?://)|(?:www))[^\s]+", "gi")
    const html = value.replace(regExp, (match) => `<a href="${match}" target="${target}">${match}</a>`);
    return this.domSanitizer.bypassSecurityTrustHtml(html);
  }
}
