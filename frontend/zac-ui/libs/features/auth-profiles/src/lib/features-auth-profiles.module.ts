import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FeaturesAuthProfilesComponent } from './features-auth-profiles.component';
import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatChipsModule } from '@angular/material/chips';
import { RolesComponent } from './roles/roles.component';
import { AuthProfilesComponent } from './auth-profiles/auth-profiles.component';
import { AddAuthProfileComponent } from './auth-profiles/add-auth-profile/add-auth-profile.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { AuthProfilesPipe } from './auth-profiles/auth-profiles.pipe';
import { UserGroupsComponent } from './user-groups/user-groups.component';
import { CreateGroupComponent } from './user-groups/create-group/create-group.component';
import { DeleteGroupComponent } from './user-groups/delete-group/delete-group.component';
import { DeleteAuthProfileComponent } from './auth-profiles/delete-auth-profile/delete-auth-profile.component';

@NgModule({
  imports: [
    CommonModule,
    SharedUiComponentsModule,
    MultiselectModule,
    MatExpansionModule,
    MatChipsModule,
    ReactiveFormsModule,
    FormsModule
  ],
  exports: [
    FeaturesAuthProfilesComponent
  ],
  declarations: [
    FeaturesAuthProfilesComponent,
    RolesComponent,
    AuthProfilesComponent,
    AddAuthProfileComponent,
    AuthProfilesPipe,
    UserGroupsComponent,
    CreateGroupComponent,
    DeleteGroupComponent,
    DeleteAuthProfileComponent
  ],
})
export class FeaturesAuthProfilesModule {}
