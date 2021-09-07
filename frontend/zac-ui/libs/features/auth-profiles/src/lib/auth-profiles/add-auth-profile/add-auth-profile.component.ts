import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FeaturesAuthProfilesService } from '../../features-auth-profiles.service';
import { HttpErrorResponse } from '@angular/common/http';
import { ModalService, SnackbarService } from '@gu/components';
import { AuthProfile, MetaConfidentiality, MetaZaaktype, Role } from '@gu/models';
import { FormArray, FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';

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
      bluePrintPermissions: this.fb.array([
        this.fb.group({
          role: ["", Validators.required],
          policies: [[], Validators.required]
        })
      ]),
    })
  }

  ngOnInit(): void {
    this.getCaseTypes();
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
   * Submit form
   */
  formSubmit() {
    this.isLoading = true;
    const formData = {
      name: this.authProfileNameControl.value,
      blueprintPermissions: [
        {
          role: this.roleControl(0).value,
          objectType: "search_report",
          policies: [
            {
              zaaktypen: this.zaaktypeControl(0).value
            }
          ]
        }
      ]
    };
    this.fService.createAuthProfile(formData).subscribe(
      () => {
        this.closeModal('add-auth-profile-modal');
        this.snackbarService.openSnackBar(this.createAuthProfileSuccessMessage, 'Sluiten', 'primary');
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

}
