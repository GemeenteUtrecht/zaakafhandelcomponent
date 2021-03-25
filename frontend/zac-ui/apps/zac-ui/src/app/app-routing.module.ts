import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { HomeComponent } from './components/home/home.component';

const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    component: HomeComponent,
  },
  {
    path: 'kownsl',
    loadChildren: () => import('./components/kownsl/kownsl.module')
      .then(m => m.KownslModule)
  },
  {
    path: 'werkvoorraad',
    loadChildren: () => import('./components/workstack/workstack.module')
      .then(m => m.WorkstackModule)
  },
  {
    path: 'zaken',
    loadChildren: () => import('./components/zaken/zaken.module')
      .then(m => m.ZakenModule)
  },
  {
    path: 'zoeken',
    loadChildren: () => import('./components/search/search.module')
      .then(m => m.SearchModule)
  },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
