import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { KetenProcessenComponent } from './keten-processen.component';

import { AdviserenAccorderenComponent } from './configuration-components/adviseren-accorderen/adviseren-accorderen.component';
import { MultiselectModule, SharedUiComponentsModule } from '@gu/components';
import { DocumentSelectComponent } from './configuration-components/document-select/document-select.component';
import { SignDocumentComponent } from './configuration-components/sign-document/sign-document.component';
import { DynamicFormComponent } from './configuration-components/dynamic-form/dynamic-form.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

@NgModule({
  declarations: [
    KetenProcessenComponent,
    AdviserenAccorderenComponent,
    DocumentSelectComponent,
    SignDocumentComponent,
    DynamicFormComponent,
  ],
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MultiselectModule,
    SharedUiComponentsModule,
  ],
  exports: [
    KetenProcessenComponent
  ]
})
export class KetenProcessenModule { }
