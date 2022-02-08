import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CapitalizePipe } from './pipes/capitalize.pipe';
import { NiceDateFormatPipe } from './pipes/nice-date-format.pipe';
import { UrlizePipe } from './pipes/urlize.pipe';

@NgModule({
  imports: [CommonModule],
  declarations: [
    CapitalizePipe,
    NiceDateFormatPipe,
    UrlizePipe,
  ],
  exports: [
    CapitalizePipe,
    NiceDateFormatPipe,
    UrlizePipe,
  ],
})
export class SharedUtilsModule {}
