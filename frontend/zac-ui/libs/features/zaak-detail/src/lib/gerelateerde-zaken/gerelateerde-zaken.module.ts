import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { GerelateerdeZakenComponent } from './gerelateerde-zaken.component';
import { RelatieToevoegenComponent } from './relatie-toevoegen/relatie-toevoegen.component';

@NgModule({
  declarations: [
    GerelateerdeZakenComponent,
    RelatieToevoegenComponent
  ],
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MultiselectModule,
    SharedUiComponentsModule,
  ],
  exports: [
    GerelateerdeZakenComponent
  ]
})
export class GerelateerdeZakenModule { }
