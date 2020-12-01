import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { MatIconModule } from '@angular/material/icon';

// UI components
import { ButtonComponent } from './button/button.component';
import { FileComponent } from './file/file.component';
import { RadioComponent } from './radio/radio.component';
import { TableComponent } from './table/table.component';

@NgModule({
  imports: [CommonModule, MatIconModule],
  declarations: [
    ButtonComponent,
    FileComponent,
    RadioComponent,
    TableComponent,
  ],
  exports: [
    ButtonComponent,
    FileComponent,
    RadioComponent,
    TableComponent,
  ],
})
export class SharedUiComponentsModule {}
