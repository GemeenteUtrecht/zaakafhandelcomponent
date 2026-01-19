import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { GerelateerdeZakenComponent } from './gerelateerde-zaken.component';
import { RelatieToevoegenComponent } from './relatie-toevoegen/relatie-toevoegen.component';
import {FeaturesSearchModule} from '@gu/search';

@NgModule({
  declarations: [
    GerelateerdeZakenComponent,
    RelatieToevoegenComponent
  ],
  imports: [
    CommonModule,
    FeaturesSearchModule,
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
