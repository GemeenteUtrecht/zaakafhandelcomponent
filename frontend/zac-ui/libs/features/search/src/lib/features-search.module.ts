import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';
import { FormGroupDirective, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';

import { FeaturesSearchComponent } from './features-search.component';
import { SearchFormComponent } from './search-form/search-form.component';
import { SearchResultsComponent } from './search-results/search-results.component';

@NgModule({
  imports: [
    CommonModule,
    HttpClientModule,
    HttpClientXsrfModule.withOptions({
      cookieName: 'csrftoken',
      headerName: 'X-CSRFToken',
    }),
    FormsModule,
    ReactiveFormsModule,
    SharedUiComponentsModule,
    MultiselectModule,
  ],
  exports: [FeaturesSearchComponent],
  declarations: [FeaturesSearchComponent, SearchFormComponent, SearchResultsComponent],
  providers: [FormGroupDirective]
})
export class FeaturesSearchModule {}
