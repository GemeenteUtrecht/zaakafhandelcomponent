import {
  Injector,
  Pipe,
  PipeTransform
} from '@angular/core';
@Pipe({
  name: 'filterResultsPipe'
})
export class FilterResultsPipe implements PipeTransform {

  public constructor(private readonly injector: Injector) {
  }

  transform(value: Array<any>, type: string): any {
    return value.filter(res => res.type === type);
  }
}
