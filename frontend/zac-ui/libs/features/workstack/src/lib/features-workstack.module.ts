import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FeaturesWorkstackComponent } from './features-workstack.component';
import { HttpClientModule, HttpClientXsrfModule } from '@angular/common/http';
import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';
import { TabsModule } from 'ngx-bootstrap/tabs';
import { AccessRequestComponent } from './access-request/access-request.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { WorkstackCasesComponent } from './tabs/workstack-cases/workstack-cases.component';
import { WorkstackTasksComponent } from './tabs/workstack-tasks/workstack-tasks.component';
import { WorkstackReviewRequestsComponent } from './tabs/workstack-review-requests/workstack-review-requests.component';
import { WorkstackActivitiesComponent } from './tabs/workstack-activities/workstack-activities.component';
import { WorkstackAccessRequestsComponent } from './tabs/workstack-access-requests/workstack-access-requests.component';

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
    MultiselectModule,
    ReactiveFormsModule,
    SharedUiComponentsModule,
    TabsModule.forRoot()
  ],
  declarations: [FeaturesWorkstackComponent, AccessRequestComponent, WorkstackCasesComponent, WorkstackTasksComponent, WorkstackReviewRequestsComponent, WorkstackActivitiesComponent, WorkstackAccessRequestsComponent],
  exports: [FeaturesWorkstackComponent],
})
export class FeaturesWorkstackModule {}
