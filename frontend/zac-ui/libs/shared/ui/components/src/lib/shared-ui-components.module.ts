import { CUSTOM_ELEMENTS_SCHEMA, NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

// Material Icons
import { MatIconModule } from '@angular/material/icon';

// External Components
import { NgbModule } from '@ng-bootstrap/ng-bootstrap';
import { BsDatepickerModule, BsLocaleService  } from 'ngx-bootstrap/datepicker';

// UI Elements
import { ButtonComponent } from './elements/button/button.component';
import { ChipComponent } from './elements/chip/chip.component';
import { LoadingIndicatorComponent } from './elements/loading-indicator/loading-indicator.component';
import { RadioComponent } from './elements/radio/radio.component';
import { TooltipComponent } from './elements/tooltip/tooltip.component';
import { CollapsibleComponent } from './elements/collapsible/collapsible.component';
import { ProgressBarComponent } from './elements/progress-bar/progress-bar.component';
import { CheckboxComponent } from './elements/checkbox/checkbox.component';
import { TextFieldComponent } from './elements/text-field/text-field.component';
import { DropdownComponent } from './elements/dropdown/dropdown.component';

// UI Components
import { FileComponent } from './components/file/file.component';
import { FileUploadComponent } from './components/file-upload/file-upload.component';
import { SuccessComponent } from './components/success/success.component';
import { ModalComponent } from './components/modal/modal.component';
import { IconComponent } from './elements/icon/icon.component';
import { DatepickerComponent } from './components/datepicker/datepicker.component';
import { TableComponent } from './components/table/table.component';
import { MessageComponent } from './elements/message/message.component';

@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatIconModule,
    NgbModule,
    BsDatepickerModule.forRoot()
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
    TextFieldComponent,
    DropdownComponent,
    MessageComponent,
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
    MatIconModule,
    TextFieldComponent,
    DropdownComponent,
    MessageComponent
  ],
  providers: [
    BsLocaleService
  ],
  schemas: [CUSTOM_ELEMENTS_SCHEMA],
})
export class SharedUiComponentsModule {}
