import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';

@Component({
  selector: 'gu-dynamic-form',
  templateUrl: './dynamic-form.component.html',
  styleUrls: ['../configuration-components.scss']
})
export class DynamicFormComponent implements OnInit {
  dynamicForm: FormGroup;
  constructor(private fb: FormBuilder,) { }

  ngOnInit(): void {
    this.dynamicForm = this.fb.group({
      test: this.fb.control("", Validators.required),
    })
  }

}
