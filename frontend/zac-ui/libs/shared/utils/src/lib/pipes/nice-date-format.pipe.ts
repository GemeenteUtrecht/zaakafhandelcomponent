import { Pipe, PipeTransform } from '@angular/core';
import { DatePipe } from '@angular/common';

@Pipe({
  name: 'niceDateFormatPipe',
})

export class NiceDateFormatPipe implements PipeTransform {
  transform(value: string|Date) {

    const dateValue = new Date(value);

    const dif = Math.floor( ( (Date.now() - dateValue.getTime()) / 1000 ) / 86400 );
    if ( dif < 30 ){
      return convertToNiceDate(value);
    } else {
      const datePipe = new DatePipe("nl-NL");
      value = datePipe.transform(value, "longDate");
      return value;
    }
  }
}

const convertToNiceDate = (time: string|Date) => {
  const date = new Date(time),
    diff = (((new Date()).getTime() - date.getTime()) / 1000),
    dayDiff = Math.floor(diff / 86400);

  if (isNaN(dayDiff) || dayDiff < 0 || dayDiff >= 31)
    return '';

  return dayDiff === 0 && (
    diff < 60 && "Zojuist" ||
    diff < 120 && "1 minuut geleden" ||
    diff < 3600 && Math.floor(diff / 60) + " minuten geleden" ||
    diff < 7200 && "1 uur geleden" ||
    diff < 86400 && Math.floor(diff / 3600) + " uur geleden") ||
    dayDiff === 1 && "Gisteren" ||
    dayDiff < 31 && dayDiff + " dagen geleden"
}
