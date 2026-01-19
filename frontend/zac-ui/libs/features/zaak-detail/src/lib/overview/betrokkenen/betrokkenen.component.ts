import { Component, Input, OnChanges } from '@angular/core';
import { AccountsService, CamundaService, MetaService, ZaakService } from '@gu/services';
import { FieldConfiguration, ModalService, SnackbarService } from '@gu/components';
import {
  Betrokkene,
  CreateBetrokkene,
  MetaRoltype,
  Oudbehandelaren,
  RowData,
  Table,
  UserSearchResult,
  Zaak
} from '@gu/models';
import { UntypedFormBuilder, UntypedFormControl, UntypedFormGroup, Validators } from '@angular/forms';

@Component({
  selector: 'gu-betrokkenen',
  templateUrl: './betrokkenen.component.html',
  styleUrls: ['./betrokkenen.component.scss']
})
export class BetrokkenenComponent implements OnChanges {
  @Input() zaak: Zaak;

  readonly omschrijvingHoofdbehandelaar = "Hoofdbehandelaar"
  hiddenRoleData: Betrokkene[];
  alwaysVisibleRoleData: Betrokkene[];
  hoofdbehandelaar: Betrokkene;
  nBehandelaars: number;
  allRoleData: Betrokkene[];
  isLoading = true;
  isExpanded: boolean;
  errorMessage: string;

  edit = false;
  users: UserSearchResult[];
  roleTypes: MetaRoltype[];
  hoofdBehandelaarType: MetaRoltype;

  roleForm: UntypedFormGroup;
  isSubmitting: boolean;
  oudbehandelaren: Oudbehandelaren;
  oudbehandelarenTable: Table = new Table(['Naam', 'E-mail', 'Start', 'Eind'], []);

  constructor(
    private zaakService: ZaakService,
    private metaService: MetaService,
    private camundaService: CamundaService,
    private accountsService: AccountsService,
    private snackbarService: SnackbarService,
    private modalService: ModalService,
    private fb: UntypedFormBuilder,
  ) { }

  // Getters / setters

  get medewerkerControl() {
    return this.roleForm.get('medewerker') as UntypedFormControl;
  }

  get roltypeControl() {
    return this.roleForm.get('roltype') as UntypedFormControl;
  }

  get changeBehandelaarControl(): UntypedFormControl {
    return this.roleForm.get('changeBehandelaar') as UntypedFormControl;
  };

  /**
   * Check if delete button should be shown
   * @param role
   * @returns {boolean}
   */
  isRemovableRole(role) {
    return this.edit && (role.omschrijvingGeneriek !== 'initiator') &&
      ((role.omschrijvingGeneriek !== 'behandelaar' || (role.omschrijving !== this.omschrijvingHoofdbehandelaar)) ||
        ((role.omschrijvingGeneriek === 'behandelaar' || (role.omschrijving === this.omschrijvingHoofdbehandelaar)) && this.nBehandelaars > 1))
  }

  ngOnChanges(): void {
    this.getContextData();
    this.roleForm = this.fb.group({
      medewerker: this.fb.control("", Validators.required),
      roltype: this.fb.control("", Validators.required),
      changeBehandelaar: true
    })
  }

  /**
   * Updates the component using a public interface.
   */
  public update() {
    this.getContextData();
  }

  /**
   * Get context data
   */
  getContextData() {
    this.isLoading = true;

    this.zaakService.getCaseOudbehandelaren(this.zaak.bronorganisatie, this.zaak.identificatie).subscribe((oudbehandelaren: Oudbehandelaren) => {
      this.oudbehandelaren = oudbehandelaren;
      this.createTable();
    }, () => this.oudbehandelaren = null)

    this.metaService.getRoleTypes(this.zaak.url).subscribe(roletypes => {
      this.roleTypes = roletypes;
      this.hoofdBehandelaarType = this.roleTypes.find(x => x.omschrijving === this.omschrijvingHoofdbehandelaar);
    })
    this.zaakService.getCaseRoles(this.zaak.bronorganisatie, this.zaak.identificatie).subscribe(data => {
      this.hoofdbehandelaar = data.find(x => x.omschrijving === this.omschrijvingHoofdbehandelaar);
      this.allRoleData = data.filter(x => x.omschrijving !== this.omschrijvingHoofdbehandelaar);
      this.formatRoles(this.allRoleData);
      this.isLoading = false;
      this.edit = false;
    }, error => {
      console.error(error);
      this.isLoading = false;
    })
  }

  createTable() {
    this.oudbehandelarenTable.bodyData = this.oudbehandelaren.oudbehandelaren.map( behandelaar => {
      const rowData: RowData = {
        cellData: {
          name: behandelaar.user.fullName,
          email: behandelaar.email,
          started: {
            type: 'date',
            date: behandelaar.started
          },
          ended: {
            type: 'date',
            date: behandelaar.ended
          }
        },
      }
      return rowData
    });
  }

  /**
   * Delete role from api
   * @param url
   */
  deleteRole(url) {
    this.isLoading = true;
    this.zaakService.deleteCaseRole(this.zaak.bronorganisatie, this.zaak.identificatie, url).subscribe(() => {
      this.getContextData()
    }, error => {
      this.errorMessage = 'Verwijderen van betrokkene mislukt. Let op, een zaak moet minimaal één behandelaar hebben.'
      this.reportError(error)
    })
  }

  /**
   * Slice roles for visibility
   * @param data
   */
  formatRoles(data: Betrokkene[]) {
    this.hiddenRoleData = data.slice(0, -3);
    this.alwaysVisibleRoleData = data.slice(-3)
    this.nBehandelaars = data.filter(role => {
      return (role.omschrijvingGeneriek === 'behandelaar') || (role.omschrijving === this.omschrijvingHoofdbehandelaar)
    }).length;
  }

  /**
   * Change the main behandelaar.
   * @param roleUrl
   */
  changeBehandelaar(roleUrl) {
    const formData = {
      zaak: this.zaak.url,
      rol: roleUrl
    }
    this.camundaService.changeBehandelaar(formData)
      .subscribe(() => {
        setTimeout(() => {
          this.getContextData();
          this.resetForm();
        }, 3000)
      }, error => {
        this.errorMessage = 'Het overhevelen van de taken van de behandelaar is mislukt.'
        this.reportError(error);
      })
  }

  //
  // Events
  //

  /**
   * Opens or closes edit mode
   */
  toggleEdit() {
    this.edit = !this.edit;
    this.isExpanded = this.edit; // Expand roles when in edit mode
  }

  /**
   * Opens modal.
   * @param {string} id
   */
  openModal(id: string) {
    this.modalService.open(id);
  }

  /**
   * Closes modal.
   * @param {string} id
   */
  closeModal(id: string) {
    this.modalService.close(id);
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

  /**
   * Submit form
   */
  submitForm() {
    this.isSubmitting = true;

    const formData: CreateBetrokkene = {
      betrokkeneType: 'medewerker',
      roltype: this.roltypeControl.value,
      zaak: this.zaak.url,
      betrokkeneIdentificatie: {
        identificatie: this.medewerkerControl.value
      }
    }

    this.zaakService.createCaseRole(this.zaak.bronorganisatie, this.zaak.identificatie, formData)
      .subscribe((role) => {
        if (role?.url && (this.roltypeControl.value === this.hoofdBehandelaarType.url && this.changeBehandelaarControl.value)) {
          this.changeBehandelaar(role.url);
        } else {
          setTimeout(() => {
            this.getContextData();
            this.resetForm();
          }, 3000)
        }
      }, error => {
        this.errorMessage = 'Aanmaken van betrokkene mislukt'
        this.reportError(error);
      })
  }

  /**
   * Reset form and close modal
   */
  resetForm() {
    this.closeModal('betrokkene-modal');
    this.isSubmitting = false;
    this.roleForm.reset();
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    const message = error?.error?.detail || error?.error[0]?.reason || error?.error.nonFieldErrors?.join(', ') || this.errorMessage;
    this.snackbarService.openSnackBar(message, 'Sluiten', 'warn');
    console.error(error);
    this.isLoading = false;
    this.isSubmitting = false;
  }
}
