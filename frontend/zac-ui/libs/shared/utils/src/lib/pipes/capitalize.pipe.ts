import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'capitalize',
})

export class CapitalizePipe implements PipeTransform {
  transform(value: any): any {
    return value.substring(0, 1).toUpperCase() + value.substring(1);
  }
}
