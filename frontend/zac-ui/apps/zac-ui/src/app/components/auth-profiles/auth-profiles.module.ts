import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SharedUiComponentsModule } from '@gu/components';
import { AuthProfilesComponent } from './auth-profiles.component';
import { AuthProfilesRoutingModule } from './auth-profiles-routing.module';
import { FeaturesAuthProfilesModule } from '@gu/auth-profiles';

@NgModule({
  declarations: [AuthProfilesComponent],
  imports: [
    CommonModule,
    SharedUiComponentsModule,
    AuthProfilesRoutingModule,
    FeaturesAuthProfilesModule
  ],
  exports: [
    AuthProfilesComponent
  ]
})
export class AuthProfilesModule { }
