import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';
import { FormGroupDirective, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';
import { FeaturesSearchComponent } from './features-search.component';
import { SearchFormComponent } from './search-form/search-form.component';
import { SearchResultsComponent } from './search-results/search-results.component';
import {PropertySearchFormComponent} from './search-form/property-search-form/property-search-form.component';
import {ZaakObjectSearchFormComponent} from './search-form/object-search-form/zaak-object-search-form.component';
import {MatListModule} from "@angular/material/list";
import {ZaakObjectStringPipe} from "./search-form/object-search-form/zaak-object-string.pipe";

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
        RouterModule,
        MatListModule
    ],
  exports: [
    FeaturesSearchComponent,
    PropertySearchFormComponent,
    SearchResultsComponent,
    ZaakObjectSearchFormComponent,
  ],
  declarations: [
    FeaturesSearchComponent,
    ZaakObjectSearchFormComponent,
    PropertySearchFormComponent,
    SearchFormComponent,
    SearchResultsComponent,
    ZaakObjectStringPipe,
  ],
  providers: [FormGroupDirective]
})
export class FeaturesSearchModule {}
