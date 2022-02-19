import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DocumentToevoegenComponent } from './document-toevoegen/document-toevoegen.component';
import { DocumentenComponent } from './documenten.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';
import { DocumentVertrouwelijkheidWijzigenComponent } from './document-vertrouwelijkheid-wijzigen/document-vertrouwelijkheid-wijzigen.component';
import {FeaturesContezzaDocumentSearchModule} from "@gu/contezza-document-search";
import { DocumentToevoegenContezzaComponent } from './document-toevoegen-contezza/document-toevoegen-contezza.component';
import { DocumentBestandsnaamWijzigenComponent } from './document-bestandsnaam-wijzigen/document-bestandsnaam-wijzigen.component';

@NgModule({
  declarations: [
    DocumentenComponent,
    DocumentToevoegenComponent,
    DocumentVertrouwelijkheidWijzigenComponent,
    DocumentToevoegenContezzaComponent,
    DocumentBestandsnaamWijzigenComponent
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
    DocumentToevoegenComponent,
    DocumentVertrouwelijkheidWijzigenComponent
  ]
})
export class DocumentenModule { }
