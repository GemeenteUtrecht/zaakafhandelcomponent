import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FeaturesAuthProfilesService } from '../../features-auth-profiles.service';
import { HttpErrorResponse } from '@angular/common/http';
import { ModalService, SnackbarService } from '@gu/components';
import { AuthProfile, MetaConfidentiality, MetaZaaktype, Role } from '@gu/models';
import { FormArray, FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';


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
export class AddAuthProfileComponent implements OnInit {
  @Input() roles: Role[];
  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();

  readonly createAuthProfileErrorMessage = "Er is een fout opgetreden bij het aanmaken van het profiel."
  readonly createAuthProfileSuccessMessage = "Het profiel is aangemaakt."

  authProfileForm: FormGroup;

  authProfiles: AuthProfile[];
  caseTypes: MetaZaaktype;
  confidentiality: MetaConfidentiality[];

  selectedObjectType: 'zaak' | 'document' | 'search_report';

  isLoading: boolean;
  errorMessage: string;

  nBlueprintPermissions = 1;

  constructor(
    private fService: FeaturesAuthProfilesService,
    private modalService: ModalService,
    private snackbarService: SnackbarService,
    private fb: FormBuilder) {
    this.authProfileForm = this.fb.group({
      name: this.fb.control("", Validators.required),
      bluePrintPermissions: this.fb.array([this.addBlueprintPermission()]),
    })
  }

  ngOnInit(): void {
    this.getCaseTypes();
    this.getConfidentiality();
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
      (error) => console.error(error),
    );
  }

  /**
   * Fetches confidentiality types
   */
  getConfidentiality() {
    this.fService.getConfidentiality().subscribe(
      (data) => this.confidentiality = data,
      (error) => console.error(error),
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
        this.zaaktypeControl(i).value.forEach(zaaktypeId => {
          const zaaktype = this.caseTypes.results.find(caseType => caseType.identificatie === zaaktypeId);
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
    this.createProfile(formData);
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
      },
      (err: HttpErrorResponse) => {
        this.errorMessage = err.error?.name[0] || this.createAuthProfileErrorMessage;
        this.reportError(err)
      }
    )
  }

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
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
}
