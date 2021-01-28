import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { KetenProcessenComponent } from './keten-processen.component';

import { AdviserenAccorderenComponent } from './configuration-components/adviseren-accorderen/adviseren-accorderen.component';
import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';

@NgModule({
  declarations: [
    KetenProcessenComponent,
    AdviserenAccorderenComponent,
  ],
  imports: [
    CommonModule,
    MultiselectModule,
    SharedUiComponentsModule,
  ],
  exports: [
    KetenProcessenComponent
  ]
})
export class KetenProcessenModule { }
