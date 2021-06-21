import { Component, EventEmitter, Input, OnChanges, OnInit, Output } from '@angular/core';
import { AccessRequests, Request } from '../models/access-request';
import { RowData, Table, Zaak } from '@gu/models';
import { FeaturesWorkstackService } from '../features-workstack.service';
import { ModalService } from '@gu/components';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { DatePipe } from '@angular/common';

@Component({
  selector: 'gu-access-request',
  templateUrl: './access-request.component.html',
  styleUrls: ['./access-request.component.scss']
})
export class AccessRequestComponent implements OnInit {
  @Input() data: AccessRequests[];
  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();

  openedAccessRequest: AccessRequests;
  openedRequest: Request;
  accessRequestForm: FormGroup;
  result: 'approve' | 'reject';

  isSubmitting: boolean;
  hasError: boolean;
  submitSuccess: boolean;
  errorMessage: string;

  constructor(
    private fb: FormBuilder,
    private featuresWorkstackService: FeaturesWorkstackService,
    private modalService: ModalService,
    private datePipe: DatePipe) {
    this.accessRequestForm = this.fb.group({
      handlerComment: this.fb.control(""),
      endDate: this.fb.control("")
    })
  }

  ngOnInit() {
    this.accessRequestForm = this.fb.group({
      handlerComment: this.fb.control(""),
      endDate: this.fb.control("")
    })
  }

  openRequestHandler(accessRequests: AccessRequests, request: Request) {
    this.resetForm();
    this.openedAccessRequest = accessRequests;
    this.openedRequest = request;
    this.modalService.open('access-request-modal');
  }

  getZaakLink(zaak) {
    return `/zaken/${zaak.bronorganisatie}/${zaak.identificatie}`;
  }

  submitForm(result: 'approve' | 'reject', request: Request) {
    this.isSubmitting = true;
    this.result = result;
    const endDate = this.endDateControl.value ?
      this.datePipe.transform(this.endDateControl.value, "yyyy-MM-dd") :
      undefined;
    const handlerComment = this.handlerCommentControl.value ? this.handlerCommentControl.value : undefined
    const formData = {
      result: result,
      handlerComment: handlerComment,
      endDate: endDate
    }
    this.featuresWorkstackService.patchAccessRequest(request.id, formData).subscribe(() => {
      this.isSubmitting = false;
      this.hasError = false;
      this.submitSuccess = true;
    }, error => {
      console.error(error);
      this.hasError = true;
      this.errorMessage = error.detail ? error.detail : "Er is een fout opgetreden"
    })
  }

  resetForm() {
    this.accessRequestForm.reset();
    this.hasError = false;
    this.submitSuccess = false;
  }

  get handlerCommentControl(): FormControl {
    return this.accessRequestForm.get('handlerComment') as FormControl;
  };

  get endDateControl(): FormControl {
    return this.accessRequestForm.get('endDate') as FormControl;
  };

}
