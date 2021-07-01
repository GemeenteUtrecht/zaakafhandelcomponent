import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';
import {SharedUiComponentsModule} from '@gu/components';
import {UserPermissionsComponent} from './user-permissions.component'

@NgModule({
  imports: [
    CommonModule,
    SharedUiComponentsModule,
  ],
  declarations: [
    UserPermissionsComponent,
  ],
  exports: [
    UserPermissionsComponent,
  ]
})
export class UserPermissionsModule {
}
