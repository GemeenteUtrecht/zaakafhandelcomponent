import { Component, Input, OnChanges, OnInit, SimpleChanges } from '@angular/core';
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
export class DatepickerComponent implements OnInit, OnChanges {
  @Input() control: FormControl;
  @Input() label: string;
  @Input() id: string;
  @Input() placeholder: string;
  @Input() minDate: Date = new Date();
  @Input() required: boolean;
  @Input() value: Date;

  bsConfig: Partial<BsDatepickerConfig>;

  constructor(private localeService: BsLocaleService) {
    defineLocale('nl', nlLocale);
    this.localeService.use('nl');
  }

  ngOnInit() {
    if (this.control.value && (this.control.value < this.minDate)) {
      this.control.patchValue(null);
    }
  }

  ngOnChanges(changes:SimpleChanges) {
    this.bsConfig = {
      adaptivePosition: true,
      dateInputFormat: 'DD-MM-YYYY',
      minDate: this.minDate,
      showWeekNumbers: false
    }
    if (this.control.value && (this.control.value < this.minDate)) {
      this.control.patchValue(null);
    }
  }

  clearValue() {
    this.control.patchValue(null)
  }
}

