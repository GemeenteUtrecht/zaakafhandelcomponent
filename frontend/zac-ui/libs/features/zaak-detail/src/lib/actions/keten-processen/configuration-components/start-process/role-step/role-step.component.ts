import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { Betrokkene, UserSearchResult, Zaak } from '@gu/models';
import { BenodigdeRol, TaskContextData } from '../../../../../../models/task-context';
import { FormArray, FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { AccountsService, ZaakService } from '@gu/services';
import { SnackbarService } from '@gu/components';

@Component({
  selector: 'gu-role-step',
  templateUrl: './role-step.component.html',
  styleUrls: ['../start-process.component.scss']
})
export class RoleStepComponent implements OnChanges {
  @Input() zaak: Zaak;
  @Input() taskContextData: TaskContextData;
  @Input() startProcessRoleForm: FormGroup;

  @Output() submittedFields: EventEmitter<any> = new EventEmitter<any>();
  @Output() updateComponents: EventEmitter<boolean> = new EventEmitter<boolean>();

  users: UserSearchResult[];

  errorMessage: string;

  submittedRoles: number[] = [];
  submittingRoles: number[] = [];

  constructor(
    private fb: FormBuilder,
    private zaakService: ZaakService,
    private accountsService: AccountsService,
    private snackbarService: SnackbarService,
  ) { }

  //
  // Getters / setters.
  //

  get rolesControl(): FormArray {
    return this.startProcessRoleForm.get('roles') as FormArray;
  };

  roleControl(i): FormControl {
    return this.rolesControl.at(i) as FormControl;
  }

  //
  // Angular lifecycle.
  //

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.taskContextData) {
      if (changes.taskContextData.previousValue !== this.taskContextData || changes.taskContextData?.firstChange) {
        this.taskContextData.context.benodigdeRollen.sort((a, b) => a.order - b.order);
        this.startProcessRoleForm = this.fb.group({
          roles: this.addRoleControls(),
        })
        this.submittedRoles = [];
        this.submittingRoles = [];
        this.submittedFields.emit({
          submitted: 0,
          total: this.rolesControl.controls.length,
          hasValidForm: this.startProcessRoleForm.valid
        })
      }
    }
  }

  //
  // Context.
  //
  /**
   *
   * Returns the context for the given index
   * @param i
   * @returns {BenodigdeRol}
   */
  getRolesContext(i): BenodigdeRol {
    return this.taskContextData.context.benodigdeRollen[i];
  }

  /**
   * Creates form controls.
   * @returns {FormArray}
   */
  addRoleControls(): FormArray {
    const arr = this.taskContextData.context.benodigdeRollen.map(role => {
      if (role.required) {
        return this.fb.control('', Validators.required);
      } else {
        return this.fb.control('');
      }
    });
    return this.fb.array(arr);
  }

  /**
   * Checks if role is already submitted.
   * @param i
   * @returns {boolean}
   */
  isSubmittedRole(i) {
    return this.submittedRoles.indexOf(i) !== -1;
  }

  //
  // Events
  //

  /**
   * Loop and post roles
   */
  submitRoles() {
    this.rolesControl.controls.forEach((control, i) => {
      if (control.value) {
        this.postRole(i);
      }
    })
  }

  /**
   * Submits the selected role to the API.
   * @param i
   */
  postRole(i) {
    this.submittingRoles.push(i)
    const selectedRole = this.getRolesContext(i);

    let betrokkeneIdentificatie;

    // Create form data
    switch (selectedRole.betrokkeneType) {
      case "organisatorische_eenheid":
        betrokkeneIdentificatie = {
          naam: this.roleControl(i).value
        }
        break;
      case "medewerker":
        betrokkeneIdentificatie = {
          identificatie: this.roleControl(i).value
        }
        break;
      case "natuurlijk_persoon":
        betrokkeneIdentificatie = {
          geslachtsnaam: this.roleControl(i).value
        }
        break;
      case "niet_natuurlijk_persoon":
        betrokkeneIdentificatie = {
          statutaireNaam: this.roleControl(i).value
        }
        break;
      case "vestiging":
        betrokkeneIdentificatie = {
          handelsnaam: this.roleControl(i).value
        }
        break;
    }

    const newCaseRole: Betrokkene = {
      betrokkeneType: selectedRole.betrokkeneType,
      roltype: selectedRole.roltype.url,
      zaak: this.zaak.url,
      betrokkeneIdentificatie: betrokkeneIdentificatie
    }

    this.zaakService.createCaseRole(this.zaak.bronorganisatie, this.zaak.identificatie, newCaseRole)
      .subscribe(() => {
        this.submittingRoles = this.submittingRoles.filter(index => index !== i);
        this.submittedRoles.push(i);

        // Emit the total submitted roles to parent
        this.submittedFields.emit({
          submitted: this.submittedRoles.length,
          total: this.rolesControl.controls.length,
          hasValidForm: this.startProcessRoleForm.valid
        })

        if (this.submittingRoles.length === 0) {
          this.updateComponents.emit(true);
        }
        this.roleControl(i).disable()
        }, error => {
          this.submittingRoles = this.submittingRoles.filter(index => index !== i);
          this.roleControl(i).enable();
          this.errorMessage = 'Het aanmaken van de betrokkene is mislukt.'
          this.reportError(error)
      })
  }


  /**
   * Search for user accounts.
   * @param searchInput
   */
  onSearchAccounts(searchInput) {
    this.accountsService.getAccounts(searchInput).subscribe(res => {
      this.users = res.results;
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
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }

}
