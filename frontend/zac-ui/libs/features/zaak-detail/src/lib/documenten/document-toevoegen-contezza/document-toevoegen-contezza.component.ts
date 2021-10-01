import { Component, EventEmitter, Input, Output } from '@angular/core';

/**
 * Wrapper component that contains the document upload of this application
 * and the contezza document selector.
 *
 * Requires mainZaakUrl: case url
 * Requires zaaktypeurl: case type url
 * Requires bronorganisatie: organisation
 * Requires identificatie: identification
 *
 * Emits reload: event to notify that the parent component can reload.
 * Emits closeModal: event to notify that the parent component can close the modal.
 */
@Component({
  selector: 'gu-document-toevoegen-contezza',
  templateUrl: './document-toevoegen-contezza.component.html',
  styleUrls: ['./document-toevoegen-contezza.component.scss']
})
export class DocumentToevoegenContezzaComponent {
  @Input() mainZaakUrl: string;
  @Input() zaaktypeurl: string;
  @Input() bronorganisatie: string;
  @Input() identificatie: string;

  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();
  @Output() closeModal: EventEmitter<boolean> = new EventEmitter<boolean>();

}
