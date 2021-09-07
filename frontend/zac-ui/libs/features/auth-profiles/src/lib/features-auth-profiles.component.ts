import { Component, OnInit } from '@angular/core';
import { Role } from '@gu/models';
import { FeaturesAuthProfilesService } from './features-auth-profiles.service';
import { SnackbarService } from '@gu/components';

@Component({
  selector: 'gu-features-auth-profiles',
  templateUrl: './features-auth-profiles.component.html',
  styleUrls: ['./features-auth-profiles.component.scss']
})
export class FeaturesAuthProfilesComponent implements OnInit {
  readonly getRolesErrorMessage = "Er is een fout opgetreden bij het ophalen van de rollen.";

  roles: Role[];
  permissions: any;

  isLoading: boolean;
  errorMessage: string;

  constructor(
    private fService: FeaturesAuthProfilesService,
    private snackbarService: SnackbarService
  ) { }

  ngOnInit() {
    this.getRoles();
  }

  /**
   * Retrieve roles.
   */
  getRoles() {
    this.isLoading = true;
    this.fService.getRoles().subscribe(
      (data) => this.roles = data,
      (err) => {
        this.errorMessage = this.getRolesErrorMessage;
        this.reportError(err)
      }
    );
    this.isLoading = false;
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
}
