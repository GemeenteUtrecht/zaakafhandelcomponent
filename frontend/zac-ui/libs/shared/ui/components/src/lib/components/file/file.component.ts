import { Component, Input, OnInit } from '@angular/core';
import { DocumentenService } from '@gu/services';

@Component({
  selector: 'gu-file',
  templateUrl: './file.component.html',
  styleUrls: ['./file.component.scss']
})
export class FileComponent implements OnInit {

  @Input() fileName: string;
  @Input() downloadUrl: string;
  @Input() readUrl: string;
  @Input() delete = false;

  constructor(private documentenService: DocumentenService) {

  }

  ngOnInit(): void {
  }

  readDocument() {
    this.documentenService.readDocument(this.readUrl).subscribe(res => {
      // Check if Microsoft Office application file
      if (res.magicUrl.substr(0, 3) === "ms-") {
        window.open(res.magicUrl, "_self");
      } else {
        window.open(res.magicUrl, "_blank");
      }
    })
  }

}
