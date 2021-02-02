import { Component, EventEmitter, Output } from '@angular/core';

@Component({
  selector: 'gu-file-upload',
  templateUrl: './file-upload.component.html',
  styleUrls: ['./file-upload.component.scss']
})
export class FileUploadComponent {
  @Output() selectedFileOutput: EventEmitter<File> = new EventEmitter();
  @Output() fileValue: EventEmitter<File> = new EventEmitter();

  fileInput: File;
  file: File;

  constructor() { }

  handleFileChangeEvent(event: Event) {
    const element: HTMLInputElement = event.currentTarget as HTMLInputElement;
    const fileList: FileList | null = element.files;
    this.fileInput = fileList ? fileList.item(0) : null;
    this.selectedFileOutput.emit(this.fileInput);
    this.fileValue.emit(this.file);
  }

  deleteSelectedFile() {
    this.fileInput = null;
    this.selectedFileOutput.emit(null);
  }

}
