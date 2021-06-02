import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DocumentToevoegenComponent } from './document-toevoegen/document-toevoegen.component';
import { DocumentenComponent } from './documenten.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';
import { DocumentVertrouwelijkheidWijzigenComponent } from './document-vertrouwelijkheid-wijzigen/document-vertrouwelijkheid-wijzigen.component';

@NgModule({
  declarations: [
    DocumentenComponent,
    DocumentToevoegenComponent,
    DocumentVertrouwelijkheidWijzigenComponent
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
    DocumentToevoegenComponent,
    DocumentVertrouwelijkheidWijzigenComponent
  ]
})
export class DocumentenModule { }
