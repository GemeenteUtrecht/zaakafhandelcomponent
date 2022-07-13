import { Component, Input, OnChanges } from '@angular/core';
import { ZaakService } from '@gu/services';

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

  constructor(
    private zaakService: ZaakService
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

  /**
   * Slice roles for visibility
   * @param data
   */
  formatRoles(data) {
    this.alwaysVisibleRoleData = data.slice(-3)
  }
}
