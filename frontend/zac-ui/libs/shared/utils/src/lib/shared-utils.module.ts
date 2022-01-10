import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NiceDateFormatPipe } from './pipes/nice-date-format.pipe';
import { CapitalizePipe } from './pipes/capitalize.pipe';

@NgModule({
  imports: [CommonModule],
  declarations: [
    CapitalizePipe,
    NiceDateFormatPipe
  ],
  exports: [
    CapitalizePipe,
    NiceDateFormatPipe,
  ],
})
export class SharedUtilsModule {}
