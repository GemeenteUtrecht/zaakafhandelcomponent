import { Pipe, PipeTransform } from '@angular/core';

@Pipe({name: 'slugify'})
export class SlugifyPipe implements PipeTransform {
  transform(value: string): string {
    return String(value).replace(/[\s_]/g, '-');
  }
}
