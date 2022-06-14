import { ChangeDetectorRef, Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { AccessRequests, Request } from '../models/access-request';
import { Permission } from '@gu/models';
import { FeaturesWorkstackService } from '../features-workstack.service';
import { ModalService, SnackbarService } from '@gu/components';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { AccountsService } from '@gu/services';

/**
 * This components displays a list of open access requests and
 * allows users to approve or reject them.
 */
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
  permissions: Permission[];
  selectedPermissions: string[];

  isSubmitting: boolean;
  hasError: boolean;
  submitSuccess: boolean;
  errorMessage: string;

  constructor(
    private cdRef: ChangeDetectorRef,
    private fb: FormBuilder,
    private featuresWorkstackService: FeaturesWorkstackService,
    private accountsService: AccountsService,
    private modalService: ModalService,
    private snackbarService: SnackbarService,
    private datePipe: DatePipe) {
    this.accessRequestForm = this.fb.group({
      handlerComment: this.fb.control(""),
      endDate: this.fb.control("")
    })
  }

  //
  // Getters / setters.
  //

  get handlerCommentControl(): FormControl {
    return this.accessRequestForm.get('handlerComment') as FormControl;
  };

  get endDateControl(): FormControl {
    return this.accessRequestForm.get('endDate') as FormControl;
  };

  //
  // Angular lifecycle.
  //

  ngOnInit() {
    this.getContextData();
  }

  //
  // Context.
  //

  /**
   * Fetch user permissions.
   */
  getContextData() {
    this.accountsService.getPermissions()
      .subscribe( res => {
        this.permissions = res;
        this.selectedPermissions = res.map( p => p.name );
      }, error => console.error(error))
  }

  /**
   * Update selected permissions.
   * @param event
   */
  updateSelectedPermissions(event) {
    this.selectedPermissions = event.map( p => p.name );
  }

  /**
   * Create link for zaak.
   * @param zaak
   * @returns {string}
   */
  getZaakLink(zaak) {
    return `/zaken/${zaak.bronorganisatie}/${zaak.identificatie}`;
  }

  /**
   * Open modal to handle access request.
   * @param {AccessRequests} accessRequests
   * @param {Request} request
   */
  openRequestHandler(accessRequests: AccessRequests, request: Request) {
    this.resetForm();
    this.openedAccessRequest = accessRequests;
    this.openedRequest = request;
    this.modalService.open('access-request-modal');
  }

  /**
   * Submit request result.
   * @param {"approve" | "reject"} result
   * @param {Request} request
   */
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
      endDate: endDate,
      permissions: this.selectedPermissions
    }
    this.accountsService.patchAccessRequest(request.id, formData).subscribe(() => {
      this.isSubmitting = false;
      this.hasError = false;
      this.submitSuccess = true;
    }, error => {
      this.errorMessage = error.detail ? error.detail : "Fout bij het versturen van je verzoek.";
      this.reportError(error);
    })
  }

  /**
   * Reset form.
   */
  resetForm() {
    this.accessRequestForm.reset();
    this.selectedPermissions = this.permissions?.map( p => p.name );
    this.hasError = false;
    this.submitSuccess = false;
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
    this.isSubmitting = false;
  }
}
