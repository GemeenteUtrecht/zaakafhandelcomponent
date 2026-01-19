import { Component, EventEmitter, Input, Output } from '@angular/core';

@Component({
  selector: 'gu-file-upload',
  templateUrl: './file-upload.component.html',
  styleUrls: ['./file-upload.component.scss']
})
export class FileUploadComponent {
  @Input() disabled: boolean;
  @Input() required: boolean;
  @Input() buttonSize: 'extrasmall' | 'small' | 'medium' | 'large' | 'huge' = 'large'

  @Output() selectedFileOutput: EventEmitter<File> = new EventEmitter();
  @Output() fileValue: EventEmitter<File> = new EventEmitter();

  fileInput: File;
  file: File;

  constructor() { }

  resetFileInput() {
    this.fileInput = null;
    this.file = null;
  }

  handleFileChangeEvent(event: Event) {
    const element: HTMLInputElement = event.currentTarget as HTMLInputElement;
    const fileList: FileList | null = element.files;
    this.fileInput = fileList ? fileList.item(0) : null;
    this.selectedFileOutput.emit(this.fileInput);
    this.fileValue.emit(this.file);
  }

  deleteSelectedFile() {
    if (!this.disabled) {
      this.fileInput = null;
      this.selectedFileOutput.emit(null);
    }
  }

}
