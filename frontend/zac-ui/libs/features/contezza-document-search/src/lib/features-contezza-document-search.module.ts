import {CUSTOM_ELEMENTS_SCHEMA, NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';
import {FeaturesContezzaDocumentSearchComponent} from "./features-contezza-document-search.component";

@NgModule({
  imports: [CommonModule],
  declarations: [FeaturesContezzaDocumentSearchComponent],
  exports: [FeaturesContezzaDocumentSearchComponent],
  schemas: [CUSTOM_ELEMENTS_SCHEMA]
})
export class FeaturesContezzaDocumentSearchModule {
}
