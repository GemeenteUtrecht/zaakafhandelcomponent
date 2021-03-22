import { Component, Input, OnInit, TemplateRef, ViewChild } from '@angular/core';

@Component({
  selector: '[gu-tab]',
  templateUrl: './tab.component.html',
  styleUrls: ['./tab.component.scss']
})
export class GuTabComponent implements OnInit {
  @Input() tabHeading: string;
  @ViewChild('childComponentTemplate') childComponentTemplate: TemplateRef<any>;
  constructor() { }

  ngOnInit(): void {
  }

}
