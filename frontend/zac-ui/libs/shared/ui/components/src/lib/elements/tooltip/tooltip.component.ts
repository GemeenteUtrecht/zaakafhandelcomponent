import { Component, Input, OnInit } from '@angular/core';

@Component({
  selector: 'gu-tooltip',
  templateUrl: './tooltip.component.html',
  styleUrls: ['./tooltip.component.scss']
})
export class TooltipComponent implements OnInit {

  @Input() position: 'top' | 'top-center' | 'bottom' | 'absolute' = 'top'
  @Input() type: 'primary' | 'accent' | 'warn' = 'primary'
  @Input() inline: boolean;
  isHovered = false;

  constructor() { }

  ngOnInit(): void {
  }

}
