import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NiceDateFormatPipe } from './helpers/nice-date-format.pipe';

@NgModule({
  imports: [CommonModule],
  declarations: [NiceDateFormatPipe],
  exports: [NiceDateFormatPipe],
})
export class SharedUtilsModule {}
