import { Component, OnInit } from '@angular/core';
import { DatePipe } from '@angular/common';
import { AbstractControl, FormBuilder, FormGroup } from '@angular/forms';
import { AdviceService } from './advice.service';
import { AdviceForm, AdviceDocument } from '../../models/advice-form';
import { ReviewRequest } from '../../models/review-request';
import { CellData, FileUpload, Table } from '@gu/models';
import { convertBlobToString } from '@gu/utils';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'gu-features-kownsl-advice',
  templateUrl: './advice.component.html',
  styleUrls: ['../features-kownsl.component.scss']
})
export class AdviceComponent implements OnInit {
  uuid: string;

  adviceData: ReviewRequest;
  isLoading: boolean;

  isSubmitting: boolean;
  submitSuccess: boolean;
  submitFailed: boolean;

  hasError: boolean;
  errorMessage: string;

  tableData: Table = {
    headData: [],
    elementData: []
  }

  pipe = new DatePipe("nl-NL");

  adviceForm: FormGroup;
  readonly documentFormGroup = {
    "content": this.fb.control(""),
    "size": this.fb.control(""),
    "name": this.fb.control(""),
    "document": this.fb.control("")
  }

  get documents(): AbstractControl { return this.adviceForm.get('documents'); }

  constructor(
    private fb: FormBuilder,
    private adviceService: AdviceService,
    private route: ActivatedRoute
  ) { }

  ngOnInit(): void {
    this.uuid = this.route.snapshot.queryParams["uuid"];
    if (this.uuid) {
      this.fetchAdvice()
      this.adviceForm = this.fb.group({
        advice: this.fb.control(""),
        documents: this.fb.group({})
      })
    } else {
      this.errorMessage = "Er is geen geldig zaaknummer gevonden..."
    }
  }

  fetchAdvice(): void {
    this.isLoading = true;
    this.adviceService.getAdvice(this.uuid).subscribe(res => {
      const isSubmittedBefore = res.headers.get('X-Kownsl-Submitted');
      if (isSubmittedBefore === "false") {
        this.adviceData = res.body;
        this.tableData = this.createTableData(res.body);
      } else {
        this.hasError = true;
        this.errorMessage = "U heeft deze aanvraag al beantwoord.";
      }
      this.isLoading = false;
    }, res => {
      this.errorMessage = res.error.detail
      this.hasError = true;
      this.isLoading = false;
    })
  }

  createTableData(adviceData: ReviewRequest): Table {
    const tableData: Table = {
      headData: ['Adviseur', 'Gedaan op'],
      elementData: []
    }

    // Add table body data
    tableData.elementData = adviceData.reviews.map( review => {
      const author = `${review.author.firstName} ${review.author.lastName}`;
      const date = this.pipe.transform(review.created, 'short');
      const cellData: CellData = {
        cellData: {
          author: author,
          created: date
        },
        expandData: review.advice
      }
      return cellData
    });

    return tableData
  }

  async handleFileSelect(file: File, fileName: string, downloadUrl: string): Promise<void> {
    if (file) {
      const fileData: FileUpload = await this.createFileData(file, fileName, downloadUrl);
      const namedDocumentFormGroup = this.createDocumentFormGroup(fileData);
      // Check if Form Control already exists
      const fileFormControl = (this.documents as FormGroup).controls[fileName]
      if (!fileFormControl) {
        (this.documents as FormGroup).addControl(fileName, this.fb.group(namedDocumentFormGroup));
      } else {
        fileFormControl.patchValue(fileData);
      }
    } else {
      (this.documents as FormGroup).removeControl(fileName);
    }
  }

  async createFileData(file: File, fileName: string, downloadUrl: string): Promise<FileUpload> {
    return {
      content: await convertBlobToString(file),
      size: file.size,
      name: fileName,
      document: downloadUrl
    }
  }

  createDocumentFormGroup(fileData: FileUpload) {
    const namedDocumentFormGroup = this.documentFormGroup;
    namedDocumentFormGroup['content'] = this.fb.control(fileData.content);
    namedDocumentFormGroup['size'] = this.fb.control(fileData.size);
    namedDocumentFormGroup['name'] = this.fb.control(fileData.name);
    namedDocumentFormGroup['document'] = this.fb.control(fileData.document);
    return namedDocumentFormGroup;
  }

  submitForm(): void {
    let formData: AdviceForm;

    const documentGroupControls = (this.documents as FormGroup).controls;
    const documentsData: AdviceDocument[] = [];
    Object.keys(documentGroupControls).forEach(documentKey => {
      const documentData: AdviceDocument = documentGroupControls[documentKey].value;
      documentsData.push(documentData)
    })
    formData = {
      advice: this.adviceForm.controls['advice'].value,
      documents: documentsData
    }
    this.postAdvice(formData)
  }

  postAdvice(formData: AdviceForm): void {
    this.isSubmitting = true;
    this.adviceService.postAdvice(formData, this.uuid).subscribe(data => {
      this.isSubmitting = false;
      this.submitSuccess = true;
    }, error => {
      this.errorMessage = "Er is een fout opgetreden bij het verzenden van uw gegevens..."
      this.submitFailed = true;
      this.isSubmitting = false;
    })
  }
}
