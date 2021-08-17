import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';
import { FormGroupDirective, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';
import { FeaturesSearchComponent } from './features-search.component';
import { SearchFormComponent } from './search-form/search-form.component';
import { SearchResultsComponent } from './search-results/search-results.component';
import {ZaakSelectModule} from './zaak-select/zaak-select.module';
import {PropertySearchFormComponent} from './search-form/property-search-form/property-search-form.component';
import {ObjectSearchFormComponent} from './search-form/object-search-form/object-search-form.component';
import {MatListModule} from "@angular/material/list";

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
        ZaakSelectModule,
        RouterModule,
        MatListModule
    ],
  exports: [
    FeaturesSearchComponent,
  ],
  declarations: [
    FeaturesSearchComponent,
    ObjectSearchFormComponent,
    PropertySearchFormComponent,
    SearchFormComponent,
    SearchResultsComponent
  ],
  providers: [FormGroupDirective]
})
export class FeaturesSearchModule {}
