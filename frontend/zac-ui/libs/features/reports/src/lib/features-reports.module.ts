import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FeaturesReportsComponent } from './features-reports.component';
import { HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';
import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';
import { TabsModule } from 'ngx-bootstrap/tabs';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    HttpClientModule,
    HttpClientXsrfModule.withOptions({
      cookieName: 'csrftoken',
      headerName: 'X-CSRFToken',
    }),
    SharedUiComponentsModule,
    MultiselectModule,
    TabsModule.forRoot(),
  ],
  declarations: [FeaturesReportsComponent],
  exports: [FeaturesReportsComponent],
})
export class FeaturesReportsModule {}
