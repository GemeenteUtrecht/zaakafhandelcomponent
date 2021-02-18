import { Component, Input } from '@angular/core';
import { ControlContainer, FormControl, NgForm } from '@angular/forms';
import { BsDatepickerConfig, BsLocaleService } from 'ngx-bootstrap/datepicker';
import { defineLocale } from 'ngx-bootstrap/chronos';
import { nlLocale } from 'ngx-bootstrap/locale';

@Component({
  selector: 'gu-datepicker',
  templateUrl: './datepicker.component.html',
  styleUrls: ['./datepicker.component.scss'],
  viewProviders: [ { provide: ControlContainer, useExisting: NgForm } ]
})
export class DatepickerComponent {
  @Input() control: FormControl;
  @Input() label: string;
  @Input() id: string;
  @Input() placeholder: string;
  @Input() minDate: Date = new Date();
  @Input() required: boolean;

  bsConfig: Partial<BsDatepickerConfig>;

  constructor(private localeService: BsLocaleService) {
    defineLocale('nl', nlLocale);
    this.localeService.use('nl');
    this.bsConfig = {
      adaptivePosition: true,
      dateInputFormat: 'DD-MM-YYYY',
      minDate: this.minDate,
      showWeekNumbers: false
    }
  }

  clearValue() {
    this.control.patchValue(undefined)
  }
}

