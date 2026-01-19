import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {AuthProfile, Role} from "@gu/models";
import {FeaturesAuthProfilesService} from "../../features-auth-profiles.service";
import {ModalService, SnackbarService} from "@gu/components";

@Component({
  selector: 'gu-delete-auth-profile',
  templateUrl: './delete-auth-profile.component.html',
  styleUrls: ['./delete-auth-profile.component.scss']
})
export class DeleteAuthProfileComponent {
  @Input() selectedAuthProfile: AuthProfile;
  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();

  isLoading: boolean;

  constructor(
    private fService: FeaturesAuthProfilesService,
    private modalService: ModalService,
    private snackbarService: SnackbarService,
  ) { }

  //
  // Context.
  //

  /**
   * Close current modal.
   */
  closeModal() {
    this.modalService.close('delete-auth-profile-modal');
  }

  /**
   * Delete selected auth profile.
   */
  deleteAuthProfile() {
    this.isLoading = true;
    this.fService.deleteAuthProfile(this.selectedAuthProfile.uuid).subscribe( () => {
      this.snackbarService.openSnackBar('Autorisatieprofiel verwijderd', 'Sluiten', 'primary');
      this.isLoading = false;
      this.reload.emit(true);
    }, () => {
      this.snackbarService.openSnackBar('Verwijderen van autorisatieprofiel niet gelukt.', 'Sluiten', 'warn');
      this.isLoading = false;
    })
  }

}
