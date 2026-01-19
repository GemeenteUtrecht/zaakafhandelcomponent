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
import { StartProcessComponent } from './configuration-components/start-process/start-process.component';
import { MatStepperModule } from '@angular/material/stepper';
import { RoleStepComponent } from './configuration-components/start-process/role-step/role-step.component';
import { PropertiesStepComponent } from './configuration-components/start-process/properties-step/properties-step.component';
import { DocumentsStepComponent } from './configuration-components/start-process/documents-step/documents-step.component';
import { SetResultComponent } from './configuration-components/set-result/set-result.component';
import { MatFormFieldModule } from '@angular/material/form-field';

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
    StartProcessComponent,
    RoleStepComponent,
    PropertiesStepComponent,
    DocumentsStepComponent,
    SetResultComponent
  ],
  imports: [
    CommonModule,
    FormsModule,
    MatStepperModule,
    MatTabsModule,
    MultiselectModule,
    ReactiveFormsModule,
    SharedUiComponentsModule,
    MatProgressBarModule,
    SharedUtilsModule,
    MatFormFieldModule
  ],
  exports: [
    KetenProcessenComponent
  ],
  providers: [
    DatePipe
  ]
})
export class KetenProcessenModule { }
