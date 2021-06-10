import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import {FormComponent} from './form.component';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import {MultiselectModule, SharedUiComponentsModule } from '@gu/components';

@NgModule({
    imports: [
        CommonModule,
        FormsModule,
        ReactiveFormsModule,
        SharedUiComponentsModule,
        MultiselectModule,
    ],
    declarations: [
        FormComponent,
    ],
    exports: [
        FormComponent,
    ]
})
export class FormModule { }
