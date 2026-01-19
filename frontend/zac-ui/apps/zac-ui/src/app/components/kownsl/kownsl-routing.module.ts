import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { KownslComponent } from './kownsl.component';

const routes: Routes = [
  {
    path: '',
    component: KownslComponent,
    children: [
      {
        path: 'review-request',
        loadChildren: () => import('@gu/kownsl')
          .then(m => m.FeaturesKownslModule)
      }
    ]
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class KownslRoutingModule { }
