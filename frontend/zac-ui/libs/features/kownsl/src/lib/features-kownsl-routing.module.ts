import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { ApprovalComponent } from './approval/approval.component';
import { AdviceComponent } from './advice/advice.component';
import { FeaturesKownslComponent } from './features-kownsl.component';

const routes: Routes = [
  {
    path: '',
    component: FeaturesKownslComponent,
    // pathMatch: 'full',
    // redirectTo: '/'
    children: [
      {
        path: 'advice',
        component: AdviceComponent
      },
      {
        path: 'approval',
        component: ApprovalComponent
      }
    ]
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class FeaturesKownslRoutingModule { }
