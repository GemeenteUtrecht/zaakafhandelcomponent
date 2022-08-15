import { Component, Input, OnChanges } from '@angular/core';
import { ZaakService } from '@gu/services';
import { ModalService, SnackbarService } from '@gu/components';

@Component({
  selector: 'gu-betrokkenen',
  templateUrl: './betrokkenen.component.html',
  styleUrls: ['./betrokkenen.component.scss']
})
export class BetrokkenenComponent implements OnChanges {
  @Input() bronorganisatie: string;
  @Input() identificatie: string;

  hiddenRoleData: any;
  alwaysVisibleRoleData: any;
  allRoleData: any;
  isLoading = true;
  isExpanded: boolean;
  errorMessage: string;

  edit = false

  constructor(
    private zaakService: ZaakService,
    private snackbarService: SnackbarService,
    private modalService: ModalService
  ) { }

  ngOnChanges(): void {
    this.getContextData();
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
    this.zaakService.getCaseRoles(this.bronorganisatie, this.identificatie).subscribe(data => {
      this.allRoleData = data;
      this.hiddenRoleData = data.slice(0, -3);
      this.alwaysVisibleRoleData = data.slice(-3)
      this.isLoading = false;
    }, error => {
      console.error(error);
      this.isLoading = false;
    })
  }

  deleteRole(url) {
    this.isLoading = true;
    const formData = {
      body: {
        url: url
      }
    };
    this.zaakService.deleteCaseRole(this.bronorganisatie, this.identificatie, formData).subscribe(() => {
      this.getContextData()
      this.edit = false;
    }, error => {
      this.errorMessage = 'Verwijderen van betrokkene mislukt.'
      this.reportError(error)
    })
  }

  /**
   * Slice roles for visibility
   * @param data
   */
  formatRoles(data) {
    this.alwaysVisibleRoleData = data.slice(-3)
  }

  //
  // Events
  //

  toggleEdit() {
    this.edit = !this.edit;

    // Expand roles when in edit mode
    this.isExpanded = this.edit;
  }

  /**
   * Opens modal.
   * @param {string} id
   */
  openModal(id: string) {
    this.modalService.open(id);
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
    this.isLoading = false;
    console.error(error);
  }
}
