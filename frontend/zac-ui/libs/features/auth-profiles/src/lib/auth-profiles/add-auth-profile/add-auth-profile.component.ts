import {
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnInit,
  Output, QueryList,
  SimpleChanges, ViewChildren
} from '@angular/core';
import { FeaturesAuthProfilesService } from '../../features-auth-profiles.service';
import { Choice, ModalService, PaginatorComponent, SnackbarService } from '@gu/components';
import {
  AuthProfile,
  MetaConfidentiality,
  MetaZaaktypeResult,
  Role, User,
  UserAuthProfile, UserAuthProfiles,
  UserSearchResult,
  ZaakPolicy
} from '@gu/models';
import { UntypedFormArray, UntypedFormBuilder, UntypedFormControl, UntypedFormGroup, Validators } from '@angular/forms';
import {MetaService} from "@gu/services";
import { atleastOneValidator } from '@gu/utils';


/**
 * A form to add authorisation profiles.
 *
 * An authorisation profile consists of roles and case types.
 * The user is allowed to assign multiple roles and case types
 * to an authorisation profile. The case types will also be given
 * a confidentiality level.
 */
@Component({
  selector: 'gu-add-auth-profile',
  templateUrl: './add-auth-profile.component.html',
  styleUrls: ['./add-auth-profile.component.scss']
})
export class AddAuthProfileComponent implements OnInit, OnChanges {
  @ViewChildren(PaginatorComponent) paginators: QueryList<PaginatorComponent>;
  @Input() type: "create" | "edit";
  @Input() selectedAuthProfile: AuthProfile;
  @Input() selectedAuthProfileUuid: string;
  @Input() roles: Role[];
  @Input() preselectedUsers: User[];
  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();

  readonly createAuthProfileSuccessMessage = "Het profiel is aangemaakt."
  readonly updateAuthProfileSuccessMessage = "Het profiel is bijgewerkt."

  readonly getAuthProfilesErrorMessage = "Er is een fout opgetreden bij het ophalen van de autorisatieprofielen.";
  authProfileForm: UntypedFormGroup;
  currentAuthProfileUuid: string;

  caseTypes: MetaZaaktypeResult[];
  caseTypeChoices: Choice[];

  confidentiality: MetaConfidentiality[];
  selectedObjectType: 'zaak' | 'document' | 'search_report';

  currentSearchValue: string;
  searchResultUsers: UserSearchResult[];
  selectedUsers: UserSearchResult[] | User[] = [];
  selectedUserAuthProfiles: UserAuthProfile[];
  removedUsers: UserAuthProfile[] = [];
  removedUsersAuthProfiles: UserAuthProfile[];
  newUsers: any = [];

  userAuthProfiles: UserAuthProfile[] = [];

  isLoading: boolean;
  errorMessage: string;

  nBlueprintPermissions = 1;

  page = 1;
  resultLength = 0;

  constructor(
    private fService: FeaturesAuthProfilesService,
    private metaService: MetaService,
    private modalService: ModalService,
    private snackbarService: SnackbarService,
    private cdRef: ChangeDetectorRef,
    private fb: UntypedFormBuilder) {
    this.authProfileForm = this.fb.group({
      name: this.fb.control("", Validators.required),
      searchValue: this.fb.control(""),
      bluePrintPermissions: this.fb.array([this.addBlueprintPermission()], atleastOneValidator()),
      mode: this.fb.control("none")
    })
  }

  //
  // Getters / setters.
  //

  get modeControl() {
    return this.authProfileForm.get('mode') as UntypedFormControl;
  }

  get authProfileNameControl() {
    return this.authProfileForm.get('name') as UntypedFormControl;
  }

  get searchValueControl() {
    return this.authProfileForm.get('searchValue') as UntypedFormControl;
  }

  get blueprintPermissionControl() {
    return this.authProfileForm.get('bluePrintPermissions') as UntypedFormArray;
  }

  roleControl(i) {
    return this.blueprintPermissionControl.at(i).get('role') as UntypedFormControl;
  }

  zaaktypeControl(i) {
    return this.blueprintPermissionControl.at(i).get('policies') as UntypedFormControl;
  }

  confidentialityControl(i) {
    return this.blueprintPermissionControl.at(i).get('confidentiality') as UntypedFormControl;
  }

  //
  // Angular lifecycle.
  //

  ngOnInit(): void {
    this.getCaseTypes();
    this.getConfidentiality();
  }

  /**
   * A lifecycle hook that is called when any data-bound property of a directive changes. Define an ngOnChanges() method
   * to handle the changes.
   */
  ngOnChanges(changes: SimpleChanges): void {
    const isUpdatedAuthProfile = this.currentAuthProfileUuid !== this.selectedAuthProfileUuid;
    this.currentAuthProfileUuid = isUpdatedAuthProfile ? this.selectedAuthProfileUuid : this.currentAuthProfileUuid;

    if (isUpdatedAuthProfile) {
      this.modeControl.setValue('none');
      this.newUsers = [];
      this.removedUsers = [];
    }

    if (this.type === "edit" && this.selectedAuthProfile) {
      this.setContextEditMode(isUpdatedAuthProfile);
    }
  }

  //
  // Context.
  //

  /**
   * Set data for edit mode.
   */
  setContextEditMode(isUpdatedAuthProfile) {
    // Prefill controls if the auth profile has changed or the blueprint permissions are not filled
    if (isUpdatedAuthProfile || !this.roleControl(0).value) {
      // Set auth profile name
      this.authProfileNameControl.patchValue(this.selectedAuthProfile?.name ? this.selectedAuthProfile.name : '');

      // this.selectedUsers = this.getPreselectedUsers();
      this.getUserAuthProfiles(this.selectedAuthProfileUuid, 1);

      // Clear search results
      this.searchValueControl.patchValue('')
      this.searchResultUsers = [];

      // Clear controls
      this.blueprintPermissionControl.clear();

      // Extract permissions with object type zaak
      const relevantPermissions = this.selectedAuthProfile.blueprintPermissions.filter(x => x.objectType === "zaak");
      this.nBlueprintPermissions = relevantPermissions.length;

      // Create control for each permission
      relevantPermissions.forEach(() => {
        const bpPerm = this.addBlueprintPermission();
        this.blueprintPermissionControl.push(bpPerm)
      })
      this.cdRef.detectChanges();

      // Update values in controls
      relevantPermissions.forEach((permission, i) => {
        const policies: ZaakPolicy[] = permission.policies.map(policy => {
          return policy['zaaktypeOmschrijving']
        })
        const confidentiality = permission.policies[0]['maxVa']
        this.roleControl(i).patchValue(permission.role);
        this.zaaktypeControl(i).patchValue(policies);
        this.confidentialityControl(i).patchValue(confidentiality);
      })
    }
  }

  /**
   * Retrieve auth profiles.
   */
  getUserAuthProfiles(uuid, page?) {
    if (this.paginators && page === 1) {
      this.paginators.forEach(paginator => {
        paginator.firstPage();
      })
    }

    // Check if the uuid is present in previously requested userAuthProfiles
    this.isLoading = true;
    this.fService.getUserAuthProfiles(this.selectedAuthProfileUuid, page, 20).subscribe(
      (data: UserAuthProfiles) => {
        this.userAuthProfiles = data.results
        this.selectedUsers = this.filterUserAuthProfileUsers(this.selectedAuthProfileUuid);
        this.selectedUserAuthProfiles = this.filterUserAuthProfiles(this.selectedAuthProfileUuid);
        this.resultLength = data.count;
        this.isLoading = false;
      },
      (err) => {
        this.isLoading = false;
        this.errorMessage = this.getAuthProfilesErrorMessage;
        this.reportError(err);
      }
    );
  }

  filterUserAuthProfiles(uuid) {
    return this.userAuthProfiles.filter((profile) => profile.authProfile === uuid)
      .sort((a,b) => ((a.user.fullName || a.user.username) > (b.user.fullName || b.user.username)) ? 1 : (((b.user.fullName || b.user.username) > (a.user.fullName || a.user.username)) ? -1 : 0));
  }

  filterUserAuthProfileUsers(uuid) {
    const profiles = this.filterUserAuthProfiles(uuid);
    return profiles.map((profile) => profile.user);
  }


  /**
   * Opens modal.
   * @param id
   */
  openModal(id) {
    this.modalService.open(id)
  }

  /**
   * Closes the modal.
   * @param id
   */
  closeModal(id) {
    this.modalService.close(id);
  }

  /**
   * Fetches zaak typen
   */
  getCaseTypes() {
    this.metaService.getCaseTypes().subscribe(
      (data) => {
        this.caseTypes = data.results
        this.caseTypeChoices = this.caseTypes.map( type => {
          return {
            label: `${type.omschrijving}: ${type.catalogus.domein}`,
            value: type.omschrijving
          }
        })
      },
      this.reportError.bind(this)
    );
  }

  /**
   * Fetches confidentiality types
   */
  getConfidentiality() {
    this.metaService.listConfidentialityClassifications().subscribe(
      (data) => this.confidentiality = data,
      (error) => this.reportError.bind(this)
    );
  }

  /**
   * Create form data
   */
  formSubmit() {
    this.isLoading = true;
    const bluePrintPermissions = this.blueprintPermissionControl.controls
      .map( (bperm, i) => {
        const policies = [];
        this.zaaktypeControl(i).value.forEach(zaaktypeOmschrijving => {
          const zaakType = this.caseTypes.find((c) => c.omschrijving === zaaktypeOmschrijving);
          const policy = {
            catalogus: zaakType.catalogus.url,
            zaaktypeOmschrijving: zaaktypeOmschrijving,
            maxVa: this.confidentialityControl(i).value
          }
          policies.push(policy);
        })
        return {
          role: this.roleControl(i).value,
          objectType: "zaak",
          policies: policies
        }
      })
    const formData = {
      name: this.authProfileNameControl.value,
      blueprintPermissions: bluePrintPermissions
    };


    if (this.type === "edit" && this.selectedAuthProfile) {
      this.updateProfile(formData, this.selectedAuthProfile.uuid);
    } else {
      this.createProfile(formData);
    }
  }

  /**
   * PUT form data to API.
   * @param formData
   * @param uuid
   */
  updateProfile(formData, uuid) {
    this.fService.updateAuthProfile(formData, uuid).subscribe(
      (res) => {
        this.updateUserAuthProfiles(res.uuid);
      }, this.reportError.bind(this)
    )
  }

  /**
   * POST form data to API.
   * @param formData
   */
  createProfile(formData) {
    this.fService.createAuthProfile(formData).subscribe(
      (res) => {
        this.createUserAuthProfiles(res.uuid);
      }, this.reportError.bind(this)
    )
  }

  /**
   * POST form data to API.
   */
  createUserAuthProfiles(uuid) {
    this.fService.createUserAuthProfile(this.selectedUsers, uuid).subscribe(
      () => {
        this.closeModal('add-auth-profile-modal');
        this.snackbarService.openSnackBar(this.createAuthProfileSuccessMessage, 'Sluiten', 'primary');
        this.resetForm();
      }, this.reportError.bind(this)
    )
  }

  /**
   * POST form data to API.
   */
  updateUserAuthProfiles(uuid) {

    // Retrieve user auth profile id of each user that has to be removed

    if (this.modeControl.value === "addUser") {
      this.fService.createUserAuthProfile(this.newUsers, uuid).subscribe(
        () => {
          this.closeModal('edit-auth-profile-modal');
          this.snackbarService.openSnackBar(this.updateAuthProfileSuccessMessage, 'Sluiten', 'primary');
          this.resetForm();
        }, this.reportError.bind(this)
      )
    }

    if (this.modeControl.value === "deleteUser") {
      this.fService.deleteUserAuthProfile(this.removedUsers).subscribe(
        () => {
          this.closeModal('edit-auth-profile-modal');
          this.snackbarService.openSnackBar(this.updateAuthProfileSuccessMessage, 'Sluiten', 'primary');
          this.resetForm();
        }, this.reportError.bind(this))
    }
  }

  /**
   * Reset the form
   */
  resetForm() {
    this.authProfileForm.reset();
    this.selectedUsers = [];
    this.searchResultUsers = [];
    this.reload.emit(true)
    this.isLoading = false;
  }

  /**
   * Form Controls
   */

  addBlueprintPermission() {
    return this.fb.group({
      role: ["", Validators.required],
      policies: [[], Validators.required],
      confidentiality: ["", Validators.required]
    })
  }

  /**
   * Steps
   */
  addStep() {
    this.nBlueprintPermissions++
    this.blueprintPermissionControl.push(this.addBlueprintPermission());
  }

  deleteStep(i) {
    if (this.nBlueprintPermissions >= 1 ) {
      this.nBlueprintPermissions--
      this.blueprintPermissionControl.removeAt(i);
      this.cdRef.detectChanges();
    }
  }

  /**
   * Search accounts.
   */
  searchUsers(isForced?) {
    if ((this.searchValueControl.value !== this.currentSearchValue) || isForced) {
      this.currentSearchValue = this.searchValueControl.value;
      if (this.currentSearchValue) {
        this.fService.getAccounts(this.currentSearchValue).subscribe(res => {
          this.searchResultUsers = res.results.filter(({ id: id1 }) => !this.selectedUsers.some(({ id: id2 }) => id2 === id1));
          this.cdRef.detectChanges();
        }, error => {
          this.reportError(error)
        })
      }
    }
  }

  /**
   * When paginator fires
   * @param uuid
   * @param page
   */
  onPageSelect(uuid, page) {
    this.getUserAuthProfiles(uuid, page.pageIndex + 1);
  }

  /**
   * Update selected users array.
   * @param {UserSearchResult} user
   */
  updateSelectedUsers(user: UserSearchResult) {
    if (this.modeControl.value === 'none') {
      const isInSelectedUsers = this.isInSelectedUser(user);
      if (!isInSelectedUsers) {
        this.selectedUsers.push(user);
        this.searchResultUsers = this.searchResultUsers.filter(({ id: id1 }) => !this.selectedUsers.some(({ id: id2 }) => id2 === id1));
        this.cdRef.detectChanges();
      } else if (isInSelectedUsers) {
        const i = this.selectedUsers.findIndex(userObj => userObj.id === user.id);
        this.selectedUsers.splice(i, 1);
        this.searchUsers(true);
        this.cdRef.detectChanges();
      }
    } else if (this.modeControl.value === 'addUser') {
      this.addToNewUsers(user);
    }
  }

  addToNewUsers(user) {
    const isInNewUser = this.isInNewUser(user);
    if (!isInNewUser) {
      this.newUsers.push(user);
      this.cdRef.detectChanges();
    }
  }
  updateNewUsers(user) {
    const isInNewUser = this.isInNewUser(user);
    if (isInNewUser) {
      const i = this.newUsers.findIndex(userObj => userObj.id === user.id);
      this.newUsers.splice(i, 1);
      this.cdRef.detectChanges();
    }
  }

  addToRemovedUsers(user) {
    const isInRemovedUsers = this.isInRemovedUser(user);
    if (!isInRemovedUsers) {
      this.removedUsers.push(user);
      this.cdRef.detectChanges();
    }
  }
  updateRemovedUsers(user) {
    const isInRemovedUsers = this.isInRemovedUser(user);
    if (isInRemovedUsers) {
      const i = this.removedUsers.findIndex(userObj => userObj.id === user.id);
      this.removedUsers.splice(i, 1);
      this.cdRef.detectChanges();
    }
  }

  /**
   * Check if user exists in current selected users array.
   * @param {UserSearchResult} user
   * @returns {boolean}
   */
  isInSelectedUser(user: UserSearchResult) {
    return this.selectedUsers.some(userObj => {
      return userObj.id === user.id
    });
  }

  /**
   * Check if user exists in current selected users array.
   * @param {UserSearchResult} user
   * @returns {boolean}
   */
  isInRemovedUser(user: UserSearchResult) {
    return this.removedUsers.some(userObj => {
      return userObj.id === user.id
    });
  }

  /**
   * Check if user exists in current selected users array.
   * @param {UserSearchResult} user
   * @returns {boolean}
   */
  isInNewUser(user: UserSearchResult) {
    return this.newUsers.some(userObj => {
      return userObj.id === user.id
    });
  }

  /**
   * Convert selected users to human readible string.
   * @returns {string[]}
   */
  showSelectedUsers() {
    return this.selectedUsers.sort((a,b) => ((a.fullName || a.username) > (b.fullName || b.username)) ? 1 : (((b.fullName || b.username) > (a.fullName || a.username)) ? -1 : 0))
  }

  /**
   * Convert selected users to human readible string.
   * @returns {string[]}
   */
  showSelectedUserAuthProfiles() {
    return this.selectedUserAuthProfiles.sort((a,b) => ((a.user.fullName || a.user.username) > (b.user.fullName || b.user.username)) ? 1 : (((b.user.fullName || b.user.username) > (a.user.fullName || a.user.username)) ? -1 : 0))
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.errorMessage = error.error?.detail || 'Er is een fout opgetreden';
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    this.isLoading = false;
    console.error(error);
  }
}
