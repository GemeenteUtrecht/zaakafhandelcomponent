import {NgModule} from '@angular/core';
import {Routes, RouterModule} from '@angular/router';
import {StartCaseComponent} from './start-case.component';

const routes: Routes = [
  {
    path: '',
    component: StartCaseComponent,
  },
];

/**
 * Module responsible for routing to component.
 */
@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class StartCaseRoutingModule {
}
