import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DocumentToevoegenComponent } from './document-toevoegen/document-toevoegen.component';
import { DocumentenComponent } from './documenten.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';

@NgModule({
  declarations: [
    DocumentenComponent,
    DocumentToevoegenComponent
  ],
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MultiselectModule,
    SharedUiComponentsModule,
  ],
  exports: [
    DocumentenComponent,
    DocumentToevoegenComponent
  ]
})
export class DocumentenModule { }
