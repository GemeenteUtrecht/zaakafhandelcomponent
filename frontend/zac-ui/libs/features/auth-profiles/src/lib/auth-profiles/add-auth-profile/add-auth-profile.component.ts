import {ChangeDetectorRef, Component, EventEmitter, Input, OnChanges, OnInit, Output} from '@angular/core';
import { FeaturesAuthProfilesService } from '../../features-auth-profiles.service';
import { ModalService, SnackbarService } from '@gu/components';
import {AuthProfile, BlueprintPermission, MetaConfidentiality, MetaZaaktype, Role, ZaakPolicy} from '@gu/models';
import { FormArray, FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import {MetaService} from "@gu/services";


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
  @Input() type: "create" | "edit";
  @Input() selectedAuthProfile: AuthProfile;
  @Input() roles: Role[];
  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();

  readonly createAuthProfileSuccessMessage = "Het profiel is aangemaakt."

  authProfileForm: FormGroup;

  caseTypes: MetaZaaktype;
  confidentiality: MetaConfidentiality[];

  selectedObjectType: 'zaak' | 'document' | 'search_report';

  isLoading: boolean;
  errorMessage: string;

  nBlueprintPermissions = 1;

  constructor(
    private fService: FeaturesAuthProfilesService,
    private metaService: MetaService,
    private modalService: ModalService,
    private snackbarService: SnackbarService,
    private cdRef: ChangeDetectorRef,
    private fb: FormBuilder) {
    this.authProfileForm = this.fb.group({
      name: this.fb.control("", Validators.required),
      bluePrintPermissions: this.fb.array([this.addBlueprintPermission()]),
    })
  }

  //
  // Getters / setters.
  //

  get authProfileNameControl() {
    return this.authProfileForm.get('name') as FormControl;
  }

  get blueprintPermissionControl() {
    return this.authProfileForm.get('bluePrintPermissions') as FormArray;
  }

  roleControl(i) {
    return this.blueprintPermissionControl.at(i).get('role') as FormControl;
  }

  zaaktypeControl(i) {
    return this.blueprintPermissionControl.at(i).get('policies') as FormControl;
  }

  confidentialityControl(i) {
    return this.blueprintPermissionControl.at(i).get('confidentiality') as FormControl;
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
  ngOnChanges(): void {
    if (this.type === "edit" && this.selectedAuthProfile) {
      this.setContextEditMode();
    }
  }

  //
  // Context.
  //

  /**
   * Set data for edit mode.
   */
  setContextEditMode() {
    // Set auth profile name
    this.authProfileNameControl.patchValue(this.selectedAuthProfile.name);

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
    this.fService.getCaseTypes().subscribe(
      (data) => this.caseTypes = data,
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
          const zaaktype = this.caseTypes.results.find(caseType => caseType.omschrijving === zaaktypeOmschrijving);
          const policy = {
            catalogus: zaaktype.catalogus,
            zaaktypeOmschrijving: zaaktype.omschrijving,
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
   * PATCH form data to API.
   * @param formData
   * @param uuid
   */
  updateProfile(formData, uuid) {
    this.fService.updateAuthProfile(formData, uuid).subscribe(
      () => {
        this.closeModal('edit-auth-profile-modal');
        this.snackbarService.openSnackBar(this.createAuthProfileSuccessMessage, 'Sluiten', 'primary');
        this.authProfileForm.reset();
        this.reload.emit(true)
        this.isLoading = false;
      }, this.reportError.bind(this)
    )
  }

  /**
   * POST form data to API.
   * @param formData
   */
  createProfile(formData) {
    this.fService.createAuthProfile(formData).subscribe(
      () => {
        this.closeModal('add-auth-profile-modal');
        this.snackbarService.openSnackBar(this.createAuthProfileSuccessMessage, 'Sluiten', 'primary');
        this.authProfileForm.reset();
        this.reload.emit(true)
        this.isLoading = false;
      }, this.reportError.bind(this)
    )
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

  deleteStep() {
    this.nBlueprintPermissions--
    this.blueprintPermissionControl.removeAt(this.blueprintPermissionControl.length - 1);
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.errorMessage = error.error?.name[0] || 'Er is een fout opgetreden';
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    this.isLoading = false;
    console.error(error);
  }
}
