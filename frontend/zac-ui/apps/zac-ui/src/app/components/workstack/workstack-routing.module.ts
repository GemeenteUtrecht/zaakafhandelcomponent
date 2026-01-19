import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { WorkstackComponent } from './workstack.component';

const routes: Routes = [
  {
    path: '',
    component: WorkstackComponent,
  },
];

/**
 * Module responsible for routing to component.
 */
@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class WorkstackRoutingModule { }
