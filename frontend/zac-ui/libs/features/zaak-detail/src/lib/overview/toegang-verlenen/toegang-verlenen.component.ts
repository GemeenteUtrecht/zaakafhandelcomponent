import { ChangeDetectorRef, Component, EventEmitter, Input, OnChanges, OnInit, Output } from '@angular/core';
import { UntypedFormBuilder, UntypedFormControl, UntypedFormGroup, Validators } from '@angular/forms';
import { UserSearchResult, Zaak, UserPermission, User, Role } from '@gu/models';
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
  @Input() userPermissions: UserPermission[];

  @Output() reload: EventEmitter<any> = new EventEmitter<any>();

  users: UserSearchResult[] = [];
  requesterUser: UserSearchResult;
  selectedUser: User;

  allRoles: Role[];
  filteredRoles: Role[];
  selectedRoles: string[];
  selectedPermissions: any;
  filteredUserPermissions: any;

  grantAccessForm: UntypedFormGroup;
  isSubmitting: boolean;
  submitErrorMessage: string;

  errorMessage: string;

  constructor(
    private fb: UntypedFormBuilder,
    private http: ApplicationHttpClient,
    private accountsService: AccountsService,
    private cdRef: ChangeDetectorRef,
    private modalService: ModalService,
    private snackbarService: SnackbarService,
    private datePipe: DatePipe,
  ) {
    this.grantAccessForm = this.fb.group({
      requester: this.fb.control("", Validators.required),
      endDate: this.fb.control("")
    })
  }

  //
  // Getters / setters.
  //

  get permissionsControl(): UntypedFormControl {
    return this.grantAccessForm.get('permissions') as UntypedFormControl;
  };

  get requesterControl(): UntypedFormControl {
    return this.grantAccessForm.get('requester') as UntypedFormControl;
  };

  get endDateControl(): UntypedFormControl {
    return this.grantAccessForm.get('endDate') as UntypedFormControl;
  };

  //
  // Angular lifecycle.
  //

  ngOnInit(): void {
    this.getContextData();
  }

  ngOnChanges(): void {
    this.grantAccessForm.reset();
    this.selectedUser = null;
  }

  /**
   * Fetch user permissions.
   */
  getContextData() {
    this.accountsService.getRoles()
      .subscribe( res => {
        this.allRoles = res;
      }, error => console.error(error))
  }

  /**
   * Update selected permissions.
   * @param event
   */
  updateSelectedRoles(event) {
    this.selectedRoles = event.map( p => p.name );
    const combinedRolePermissions = [...new Set(event.flatMap(obj => obj.permissions))];
    this.selectedPermissions = combinedRolePermissions.filter(permission => !this.filteredUserPermissions.includes(permission))
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
   * Show permissions according to user
   * @param user
   */
  onUserSelect(user) {
    this.selectedUser = user;
    if (user) {
      const filteredUserPermissions = this.userPermissions.filter(permissionObject => permissionObject.username === user.username)

      // Check if selected user already has permissions
      if (filteredUserPermissions?.length > 0) {
        this.filteredUserPermissions = filteredUserPermissions[0].permissions.map(zaakPermission => zaakPermission.permission);
      } else if (filteredUserPermissions?.length === 0) {
        this.filteredUserPermissions = [];
      }
    }
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

    this.accountsService.addAtomicPermissions(this.zaak, this.requesterControl.value, this.selectedPermissions, endDate).subscribe(res => {
      // reset form
      this.grantAccessForm.reset();
      this.selectedUser = null;

      // reload and close
      this.modalService.close('add-person-modal');
      this.reload.emit();

      this.isSubmitting = false;
    }, error => {
      // create error message
      try {
        this.submitErrorMessage = (error?.error?.detail)
            ? error.error.detail
            : error.error[0].nonFieldErrors[0];
      } catch (e) {
        this.submitErrorMessage = 'Er is een fout opgetreden';
      }

      // reset form
      this.grantAccessForm.reset();
      this.selectedUser = null;
      this.getContextData();
      this.reload.emit();

      // handle error and close
      this.reportError(error);
      this.modalService.close('add-person-modal');

      this.isSubmitting = false;
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
    this.snackbarService.openSnackBar(this.submitErrorMessage, 'Sluiten', 'warn');
    console.error(error);
    this.isSubmitting = false;
  }

}
