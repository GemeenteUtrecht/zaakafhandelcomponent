import { Component, Input, OnInit } from '@angular/core';

@Component({
  selector: 'gu-text-field',
  templateUrl: './text-field.component.html',
  styleUrls: ['./text-field.component.scss']
})
export class TextFieldComponent implements OnInit {

  @Input() label: string;

  constructor() { }

  ngOnInit(): void {
  }

}
