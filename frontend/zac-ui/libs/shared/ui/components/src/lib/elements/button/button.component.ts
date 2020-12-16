import { Component, Input, OnInit } from '@angular/core';

@Component({
  selector: 'gu-button',
  templateUrl: './button.component.html',
  styleUrls: ['./button.component.scss']
})
export class ButtonComponent implements OnInit {

  @Input() type: 'primary' | 'secondary' | 'tertiary' = 'primary';
  @Input() size: 'small' | 'medium' | 'large' = 'medium';
  @Input() disabled: boolean;
  @Input() loading: boolean;

  constructor() { }

  ngOnInit(): void {
  }

}
