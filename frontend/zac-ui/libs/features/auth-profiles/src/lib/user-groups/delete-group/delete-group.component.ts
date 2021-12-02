import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { UserGroupDetail } from '@gu/models';
import { FeaturesAuthProfilesService } from '../../features-auth-profiles.service';
import { ModalService, SnackbarService } from '@gu/components';

/**
 * Delete a user group.
 */
@Component({
  selector: 'gu-delete-group',
  templateUrl: './delete-group.component.html',
  styleUrls: ['./delete-group.component.scss']
})
export class DeleteGroupComponent {
  @Input() selectedUserGroup: UserGroupDetail;
  @Output() reloadGroups: EventEmitter<any> = new EventEmitter<any>();

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
    this.modalService.close('delete-usergroup-modal');
  }

  /**
   * Delete selected user group.
   */
  deleteUserGroup() {
    this.isLoading = true;
    this.fService.deleteUserGroup(this.selectedUserGroup.id).subscribe( () => {
      this.snackbarService.openSnackBar('Gebruikersgroep verwijderd', 'Sluiten', 'primary');
      this.isLoading = false;
      this.reloadGroups.emit(true);
    }, () => {
      this.snackbarService.openSnackBar('Verwijderen van gebruikersgroep niet gelukt.', 'Sluiten', 'warn');
      this.isLoading = false;
    })
  }

}
