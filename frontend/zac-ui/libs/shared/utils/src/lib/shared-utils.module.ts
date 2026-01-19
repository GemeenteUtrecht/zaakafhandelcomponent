import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CapitalizePipe } from './pipes/capitalize.pipe';
import { NiceDateFormatPipe } from './pipes/nice-date-format.pipe';
import { UrlizePipe } from './pipes/urlize.pipe';
import {SlugifyPipe} from './pipes/slugify.pipe';

@NgModule({
  imports: [CommonModule],
  declarations: [
    CapitalizePipe,
    NiceDateFormatPipe,
    SlugifyPipe,
    UrlizePipe,
  ],
  exports: [
    CapitalizePipe,
    NiceDateFormatPipe,
    SlugifyPipe,
    UrlizePipe,
  ],
})
export class SharedUtilsModule {}
