import { Component, EventEmitter, Input, OnChanges, OnInit, Output } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { UserSearchResult, Zaak, Role } from '@gu/models';
import { AccountsService, ApplicationHttpClient } from '@gu/services';
import {ModalService, SnackbarService} from '@gu/components';
import { DatePipe } from '@angular/common';

@Component({
  selector: 'gu-toegang-verlenen',
  templateUrl: './toegang-verlenen.component.html',
  styleUrls: ['./toegang-verlenen.component.scss']
})
export class ToegangVerlenenComponent implements OnInit, OnChanges {
  @Input() zaak: Zaak;
  @Output() reload: EventEmitter<any> = new EventEmitter<any>();

  users: UserSearchResult[] = [];
  requesterUser: UserSearchResult;
  allRoles: Role[];
  multiselectRoles: object[];
  preselectedPermissions: string[];
  selectedRoles: string[] = [];

  grantAccessForm: FormGroup;
  isSubmitting: boolean;
  submitHasError: boolean;
  submitErrorMessage: string;

  submitResult: any;
  submitSuccess: boolean;
  errorMessage: string;

  constructor(
    private fb: FormBuilder,
    private http: ApplicationHttpClient,
    private accountsService: AccountsService,
    private modalService: ModalService,
    private snackbarService: SnackbarService,
    private datePipe: DatePipe,
  ) { }

  //
  // Getters / setters.
  //

  get rolesControl(): FormControl {
    return this.grantAccessForm.get('roles') as FormControl;
  };

  get requesterControl(): FormControl {
    return this.grantAccessForm.get('requester') as FormControl;
  };

  get endDateControl(): FormControl {
    return this.grantAccessForm.get('endDate') as FormControl;
  };

  //
  // Angular lifecycle.
  //

  ngOnInit(): void {
    this.grantAccessForm = this.fb.group({
      requester: this.fb.control("", Validators.required),
      endDate: this.fb.control("")
    })
    this.getContextData();
  }

  ngOnChanges() {
    this.submitSuccess = false;
  }

  /**
   * Fetch user roles and permissions.
   */
  getContextData() {
    this.accountsService.getRoles()
      .subscribe( res => {
        this.allRoles = res;
        this.multiselectRoles = res.map(({permissions, ...multiselectAttrs}) => multiselectAttrs)
      }, error => console.error(error))

    this.accountsService.getPermissions()
      .subscribe( res => {
        this.preselectedPermissions = res.map( p => p.name );
      }, error => console.error(error))
  }

  /**
   * Update selected roles.
   * @param event
   */
  updateSelectedRoles(event) {
    this.selectedRoles = event.map( p => p.name );
  }

  /**
   * Search users.
   * @param searchInput
   */
  onSearch(searchInput) {
    this.accountsService.getAccounts(searchInput).subscribe(res => {
      this.users = res.results;
    }, error => this.reportError(error)
    );
  }

  /**
   * Submit access.
   */
  submitForm() {
    this.isSubmitting = true;
    this.users.forEach(user => {
      if (user.username === this.requesterControl.value) {
        this.requesterUser = user;
      }
    })

    const endDate = this.endDateControl.value ?
      this.datePipe.transform(this.endDateControl.value, "yyyy-MM-ddT00:00") :
      undefined;

    const matchedSelectedRoles = this.allRoles.filter(role => this.selectedRoles.includes(role.name))
    const selectedPermissions =  matchedSelectedRoles.reduce((a, { permissions }) => a.concat(permissions), [])
    const filteredPermissions = selectedPermissions.filter(permission => !this.preselectedPermissions.includes(permission));

    this.accountsService.addAtomicPermissions(this.zaak, this.requesterControl.value, filteredPermissions, endDate).subscribe(res => {
      this.submitResult = {
        username: res.requester,
        name: this.requesterUser
      }

      this.submitSuccess = true;
      this.grantAccessForm.reset();
      this.submitHasError = false;
      this.isSubmitting = false;

      this.reload.emit();
    }, error => {

      try {
        this.submitErrorMessage = (error?.error?.detail)
            ? error.error.detail
            : error.error[0].nonFieldErrors[0];
      } catch (e) {
        this.submitErrorMessage = 'Er is een fout opgetreden';
      }


      this.reportError(error);
      this.modalService.close('add-person-modal');
    })
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.submitHasError = true;
    this.snackbarService.openSnackBar(this.submitErrorMessage, 'Sluiten', 'warn');
    console.error(error);
    this.isSubmitting = false;
  }

}
