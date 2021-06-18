import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FeaturesWorkstackComponent } from './features-workstack.component';
import { HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';
import { SharedUiComponentsModule } from '@gu/components';
import { TabsModule } from 'ngx-bootstrap/tabs';
import { AccessRequestComponent } from './access-request/access-request.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

@NgModule({
  imports: [
    CommonModule,
    RouterModule,
    HttpClientModule,
    HttpClientXsrfModule.withOptions({
      cookieName: 'csrftoken',
      headerName: 'X-CSRFToken',
    }),
    FormsModule,
    ReactiveFormsModule,
    SharedUiComponentsModule,
    TabsModule.forRoot()
  ],
  declarations: [FeaturesWorkstackComponent, AccessRequestComponent],
  exports: [FeaturesWorkstackComponent],
})
export class FeaturesWorkstackModule {}
