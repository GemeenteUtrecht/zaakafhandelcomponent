import { Component, Input, OnInit } from '@angular/core';

@Component({
  selector: 'gu-file',
  templateUrl: './file.component.html',
  styleUrls: ['./file.component.scss']
})
export class FileComponent implements OnInit {

  @Input() fileName: string;
  @Input() downloadUrl: string;
  @Input() delete = false;

  constructor() { }

  ngOnInit(): void {
  }

}
