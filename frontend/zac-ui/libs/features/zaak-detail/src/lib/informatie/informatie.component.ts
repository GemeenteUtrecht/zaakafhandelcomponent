import { Component, Input, OnInit } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';

@Component({
  selector: 'gu-informatie',
  templateUrl: './informatie.component.html',
  styleUrls: ['./informatie.component.scss']
})
export class InformatieComponent implements OnInit {
  @Input() data;
  isLoading: boolean;

  constructor() {}

  ngOnInit(): void {
    // this.isLoading = true;
  }
}
