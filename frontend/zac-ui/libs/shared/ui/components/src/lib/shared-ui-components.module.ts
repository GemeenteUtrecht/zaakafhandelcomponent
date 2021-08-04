import {CUSTOM_ELEMENTS_SCHEMA, NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {RouterModule} from '@angular/router';

// Material Components
import {MatCheckboxModule} from "@angular/material/checkbox";
import {MatDatepickerModule} from "@angular/material/datepicker";
import {MatFormFieldModule} from "@angular/material/form-field";
import {MatInputModule} from "@angular/material/input";
import {MatIconModule} from '@angular/material/icon';
import {MatNativeDateModule} from '@angular/material/core';
import {MatSortModule} from "@angular/material/sort";
import {MatTableModule} from '@angular/material/table';
import {MatTabsModule} from '@angular/material/tabs';

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
import {TabComponent} from './components/tabs/tab.component';
import {TabGroupComponent} from './components/tabs/tab-group.component';


@NgModule({
    imports: [
        CommonModule,
        FormsModule,
        ReactiveFormsModule,
        MatFormFieldModule,
        MatInputModule,
        MatNativeDateModule,
        MatIconModule,
        MatTableModule,
        RouterModule,
        MatSortModule,
        MatCheckboxModule,
        MatDatepickerModule,
        MatTabsModule,
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
        TabComponent,
        TabGroupComponent
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
        TabComponent,
        TabGroupComponent,
        MatTabsModule
    ],
    schemas: [CUSTOM_ELEMENTS_SCHEMA],
})
export class SharedUiComponentsModule {
}
