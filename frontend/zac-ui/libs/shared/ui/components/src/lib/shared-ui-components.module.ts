import {CUSTOM_ELEMENTS_SCHEMA, NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {RouterModule} from '@angular/router';

// Material Components
import {MatIconModule} from '@angular/material/icon';
import {MatTableModule} from '@angular/material/table';
import {MatSortModule} from "@angular/material/sort";

// External Components
import {BsDatepickerModule, BsLocaleService} from 'ngx-bootstrap/datepicker';

// UI Elements
import {ButtonComponent} from './elements/button/button.component';
import {ChipComponent} from './elements/chip/chip.component';
import {LoadingIndicatorComponent} from './elements/loading-indicator/loading-indicator.component';
import {RadioComponent} from './elements/radio/radio.component';
import {TooltipComponent} from './elements/tooltip/tooltip.component';
import {CollapsibleComponent} from './elements/collapsible/collapsible.component';
import {ProgressBarComponent} from './elements/progress-bar/progress-bar.component';
import {CheckboxComponent} from './elements/checkbox/checkbox.component';
import {InputFieldComponent} from './elements/input-field/input-field.component';
import {MessageComponent} from './elements/message/message.component';
import {IconComponent} from './elements/icon/icon.component';

// UI Components
import {FileComponent} from './components/file/file.component';
import {FileUploadComponent} from './components/file-upload/file-upload.component';
import {SuccessComponent} from './components/success/success.component';
import {ModalComponent} from './components/modal/modal.component';
import {DatepickerComponent} from './components/datepicker/datepicker.component';
import {TableComponent} from './components/table/table.component';
import {SidenavComponent} from './components/sidenav/sidenav.component';
import {BrowserAnimationsModule} from "@angular/platform-browser/animations";


@NgModule({
    imports: [
        CommonModule,
        FormsModule,
        ReactiveFormsModule,
        MatIconModule,
        MatTableModule,
        BsDatepickerModule.forRoot(),
        RouterModule,
        MatSortModule
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
        InputFieldComponent,
        MessageComponent,
        SidenavComponent,
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
        InputFieldComponent,
        MessageComponent,
        SidenavComponent,
    ],
    providers: [
        BsLocaleService
    ],
    schemas: [CUSTOM_ELEMENTS_SCHEMA],
})
export class SharedUiComponentsModule {
}
