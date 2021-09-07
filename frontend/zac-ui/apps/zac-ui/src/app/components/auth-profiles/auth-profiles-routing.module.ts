import { NgModule } from '@angular/core';
import { AuthProfilesComponent } from './auth-profiles.component';
import { RouterModule, Routes } from '@angular/router';

const routes: Routes = [
  {
    path: '',
    component: AuthProfilesComponent,
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class AuthProfilesRoutingModule { }
