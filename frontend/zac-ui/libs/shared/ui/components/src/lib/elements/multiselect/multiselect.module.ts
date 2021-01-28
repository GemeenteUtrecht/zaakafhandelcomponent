import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MultiselectComponent } from './multiselect.component';
import { NgMultiSelectDropDownModule } from 'ng-multiselect-dropdown';
import { FormsModule } from '@angular/forms';

@NgModule({
  declarations: [MultiselectComponent],
  imports: [
    CommonModule,
    FormsModule,
    NgMultiSelectDropDownModule.forRoot()
  ],
  exports: [
    MultiselectComponent
  ]
})
export class MultiselectModule { }
