import {Component, EventEmitter, Input, Output, ViewEncapsulation} from '@angular/core';
import { Zaak } from '@gu/models';

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
  styleUrls: ['./document-toevoegen-contezza.component.scss'],
  encapsulation: ViewEncapsulation.None
})
export class DocumentToevoegenContezzaComponent {
  @Input() zaak: Zaak;

  @Output() reload = new EventEmitter<boolean>();
  @Output() closeModal = new EventEmitter<boolean>();

}
