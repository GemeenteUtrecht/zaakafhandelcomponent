import { NgModule } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { KetenProcessenComponent } from './keten-processen.component';
import { AdviserenAccorderenComponent } from './configuration-components/adviseren-accorderen/adviseren-accorderen.component';
import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';
import { DocumentSelectComponent } from './configuration-components/document-select/document-select.component';
import { SignDocumentComponent } from './configuration-components/sign-document/sign-document.component';
import { DynamicFormComponent } from './configuration-components/dynamic-form/dynamic-form.component';
import { AssignTaskComponent } from './assign-task/assign-task.component';
import { RedirectComponent } from './configuration-components/redirect/redirect.component';
import {MatTabsModule} from "@angular/material/tabs";
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { SharedUtilsModule } from '@gu/utils';
import { CancelTaskComponent } from './cancel-task/cancel-task.component';

@NgModule({
  declarations: [
    KetenProcessenComponent,
    AdviserenAccorderenComponent,
    DocumentSelectComponent,
    SignDocumentComponent,
    DynamicFormComponent,
    AssignTaskComponent,
    RedirectComponent,
    CancelTaskComponent,
  ],
  imports: [
    CommonModule,
    FormsModule,
    MatTabsModule,
    MultiselectModule,
    ReactiveFormsModule,
    SharedUiComponentsModule,
    MatProgressBarModule,
    SharedUtilsModule
  ],
  exports: [
    KetenProcessenComponent
  ],
  providers: [
    DatePipe
  ]
})
export class KetenProcessenModule { }
