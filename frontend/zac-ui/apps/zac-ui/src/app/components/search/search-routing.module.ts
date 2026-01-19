import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { SearchComponent } from './search.component';

const routes: Routes = [
  { path: '', redirectTo: 'zaak', pathMatch: 'full' },
  { path: '', children: [
      { path: 'zaak', component: SearchComponent },
      { path: 'object', component: SearchComponent }
    ]
  }
];

/**
 * Module responsible for routing to component.
 */
@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class SearchRoutingModule { }
