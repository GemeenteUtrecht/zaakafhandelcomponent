import { CUSTOM_ELEMENTS_SCHEMA, NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

// Material Icons
import { MatIconModule } from '@angular/material/icon';

// Angular material components
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { NgbModule } from '@ng-bootstrap/ng-bootstrap';

// UI Elements
import { ButtonComponent } from './elements/button/button.component';
import { ChipComponent } from './elements/chip/chip.component';
import { LoadingIndicatorComponent } from './elements/loading-indicator/loading-indicator.component';
import { RadioComponent } from './elements/radio/radio.component';
import { TableComponent } from './elements/table/table.component';
import { TooltipComponent } from './elements/tooltip/tooltip.component';
import { CollapsibleComponent } from './elements/collapsible/collapsible.component';
import { ProgressBarComponent } from './elements/progress-bar/progress-bar.component';
import { CheckboxComponent } from './elements/checkbox/checkbox.component';

// UI Components
import { FileComponent } from './components/file/file.component';
import { FileUploadComponent } from './components/file-upload/file-upload.component';
import { SuccessComponent } from './components/success/success.component';
import { ModalComponent } from './components/modal/modal.component';
import { MultiselectComponent } from './elements/multiselect/multiselect.component';
import { MultiselectModule } from './elements/multiselect/multiselect.module';
import { IconComponent } from './elements/icon/icon.component';
import { DatepickerComponent } from './components/datepicker/datepicker.component';
// import { ModalModule } from './components/modal';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatIconModule,
    NgbModule,
    // MultiselectModule
    // ModalModule
  ],
  declarations: [
    ButtonComponent,
    ChipComponent,
    CollapsibleComponent,
    FileComponent,
    FileUploadComponent,
    LoadingIndicatorComponent,
    RadioComponent,
    TableComponent,
    TooltipComponent,
    SuccessComponent,
    ProgressBarComponent,
    ModalComponent,
    CheckboxComponent,
    IconComponent,
    DatepickerComponent,
    // MultiselectComponent,
  ],
  exports: [
    ButtonComponent,
    ChipComponent,
    CollapsibleComponent,
    FileComponent,
    FileUploadComponent,
    LoadingIndicatorComponent,
    RadioComponent,
    TableComponent,
    TooltipComponent,
    SuccessComponent,
    ProgressBarComponent,
    ModalComponent,
    CheckboxComponent,
    IconComponent,
    DatepickerComponent,
    // MultiselectComponent,
    MatIconModule,
  ],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
})
export class SharedUiComponentsModule {}
