import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Route } from '@angular/router';
import { FeaturesWorkstackComponent } from './features-workstack.component';
import { HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';
import { SharedUiComponentsModule } from '@gu/components';
import { TabsModule } from 'ngx-bootstrap/tabs';

export const featuresWorkstackRoutes: Route[] = [];

@NgModule({
  imports: [
    CommonModule,
    RouterModule,
    HttpClientModule,
    HttpClientXsrfModule.withOptions({
      cookieName: 'csrftoken',
      headerName: 'X-CSRFToken',
    }),
    SharedUiComponentsModule,
    TabsModule.forRoot()
  ],
  declarations: [FeaturesWorkstackComponent],
  exports: [FeaturesWorkstackComponent],
})
export class FeaturesWorkstackModule {}
