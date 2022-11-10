import { Component, Input, OnChanges } from '@angular/core';
import { AccountsService, MetaService, ZaakService } from '@gu/services';
import { FieldConfiguration, ModalService, SnackbarService } from '@gu/components';
import { Betrokkene, CreateBetrokkene, MetaRoltype, UserSearchResult, Zaak } from '@gu/models';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';

@Component({
  selector: 'gu-betrokkenen',
  templateUrl: './betrokkenen.component.html',
  styleUrls: ['./betrokkenen.component.scss']
})
export class BetrokkenenComponent implements OnChanges {
  @Input() zaak: Zaak;

  hiddenRoleData: Betrokkene[];
  alwaysVisibleRoleData: Betrokkene[];
  nBehandelaars: number;
  allRoleData: any;
  isLoading = true;
  isExpanded: boolean;
  errorMessage: string;

  edit = false;
  users: UserSearchResult[];
  roleTypes: MetaRoltype[];

  roleForm: FormGroup;
  isSubmitting: boolean;

  constructor(
    private zaakService: ZaakService,
    private metaService: MetaService,
    private accountsService: AccountsService,
    private snackbarService: SnackbarService,
    private modalService: ModalService,
    private fb: FormBuilder,
  ) { }

  // Getters / setters

  get medewerkerControl() {
    return this.roleForm.get('medewerker') as FormControl;
  }

  get roltypeControl() {
    return this.roleForm.get('roltype') as FormControl;
  }

  /**
   * Check if delete button should be shown
   * @param role
   * @returns {boolean}
   */
  isRemovableRole(role) {
    return this.edit && (role.omschrijvingGeneriek !== 'behandelaar' || (role.omschrijvingGeneriek === 'behandelaar' && this.nBehandelaars > 1))
  }

  ngOnChanges(): void {
    this.getContextData();
    this.roleForm = this.fb.group({
      medewerker: this.fb.control("", Validators.required),
      roltype: this.fb.control("", Validators.required)

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
    this.metaService.getRoleTypes(this.zaak.url).subscribe(roletypes => {
      this.roleTypes = roletypes;
    })
    this.zaakService.getCaseRoles(this.zaak.bronorganisatie, this.zaak.identificatie).subscribe(data => {
      this.allRoleData = data;
      this.formatRoles(data);
      this.isLoading = false;
      this.edit = false;
    }, error => {
      console.error(error);
      this.isLoading = false;
    })
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
      return role.omschrijvingGeneriek === 'behandelaar'
    }).length;
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
      .subscribe(() => {
        setTimeout(() => {
          this.getContextData();
          this.closeModal('betrokkene-modal');
          this.isSubmitting = false;
          this.roleForm.reset();
        }, 3000)
      }, error => {
        this.errorMessage = 'Aanmaken van betrokkene mislukt'
        this.reportError(error);
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
    const message = error?.error?.detail || error?.error.nonFieldErrors?.join(', ') || this.errorMessage;
    this.snackbarService.openSnackBar(message, 'Sluiten', 'warn');
    console.error(error);
    this.isLoading = false;
  }
}
