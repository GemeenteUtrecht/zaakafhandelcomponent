import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DocumentenComponent } from './documenten.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';
import {FeaturesContezzaDocumentSearchModule} from "@gu/contezza-document-search";
import { DocumentToevoegenContezzaComponent } from './document-toevoegen-contezza/document-toevoegen-contezza.component';
import { DocumentWijzigenComponent } from './document-wijzigen/document-wijzigen.component';

@NgModule({
  declarations: [
    DocumentenComponent,
    DocumentToevoegenContezzaComponent,
    DocumentWijzigenComponent
  ],
  imports: [
    CommonModule,
    FeaturesContezzaDocumentSearchModule,
    FormsModule,
    MultiselectModule,
    ReactiveFormsModule,
    SharedUiComponentsModule,
  ],
  exports: [
    DocumentenComponent,
    DocumentWijzigenComponent
  ]
})
export class DocumentenModule { }
