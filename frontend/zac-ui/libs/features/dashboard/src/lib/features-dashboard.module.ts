import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FeaturesDashboardComponent } from './features-dashboard.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';
import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { RouterModule } from '@angular/router';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    HttpClientModule,
    HttpClientXsrfModule.withOptions({
      cookieName: 'csrftoken',
      headerName: 'X-CSRFToken'
    }),
    SharedUiComponentsModule,
    MultiselectModule,
    MatProgressBarModule,
    RouterModule
  ],
  declarations: [FeaturesDashboardComponent],
  exports: [FeaturesDashboardComponent],
})
export class FeaturesDashboardModule {}
