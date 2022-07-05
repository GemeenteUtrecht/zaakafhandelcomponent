import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { Betrokkene, UserSearchResult, Zaak } from '@gu/models';
import { BenodigdeRol, TaskContextData } from '../../../../../../models/task-context';
import { FormArray, FormBuilder, FormControl } from '@angular/forms';
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

  @Output() submittedFields: EventEmitter<any> = new EventEmitter<any>();

  users: UserSearchResult[];

  startProcessRoleForm: any;
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
    if (changes.taskContextData.previousValue !== this.taskContextData ) {
      this.startProcessRoleForm = this.fb.group({
        roles: this.addRoleControls(),
      })
      this.submittedRoles = [];
      this.submittingRoles = [];
      this.submittedFields.emit({
        submitted: 0,
        total: this.rolesControl.controls.length
      })
    }
  }

  //
  // Context.
  //

  getRolesContext(i): BenodigdeRol {
    return this.taskContextData.context.benodigdeRollen[i];
  }

  addRoleControls(): FormArray {
    const arr = this.taskContextData.context.benodigdeRollen.map(() => {
      return this.fb.control('');
    });
    return this.fb.array(arr);
  }

  isSubmittedRole(i) {
    return this.submittedRoles.indexOf(i) !== -1;
  }

  //
  // Events
  //

  submitRole(i) {
    this.submittingRoles.push(i)
    this.roleControl(i).disable()
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
          total: this.rolesControl.controls.length
        })
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
