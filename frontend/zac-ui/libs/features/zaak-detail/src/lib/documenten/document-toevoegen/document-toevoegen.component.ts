import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { HttpResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApplicationHttpClient } from '@gu/services';
import { FileUploadComponent, ModalService } from '@gu/components';
import { Document } from '@gu/models';

@Component({
  selector: 'gu-document-toevoegen',
  templateUrl: './document-toevoegen.component.html',
  styleUrls: ['./document-toevoegen.component.scss']
})
export class DocumentToevoegenComponent {
  // TODO: LOTS OF THINGS TODO!!

  @Input() mainZaakUrl: string;
  @Input() zaaktypeurl: string;
  @Input() bronorganisatie: string;
  @Input() identificatie: string;
  @Input() activity: string;
  @Input() documentUrl?: string;
  @Input() updateDocument: boolean;
  @Input() closeButton: boolean;
  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();
  @Output() closeModal: EventEmitter<boolean> = new EventEmitter<boolean>();
  @Output() uploadedDocument: EventEmitter<Document> = new EventEmitter<Document>();
}
