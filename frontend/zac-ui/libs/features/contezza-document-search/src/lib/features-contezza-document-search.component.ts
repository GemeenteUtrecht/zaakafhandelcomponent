import {DOCUMENT} from '@angular/common';
import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  Inject,
  Input,
  OnInit,
  Output,
  Renderer2,
  ViewChild
} from '@angular/core';
import { Observable, of } from 'rxjs';
import {SnackbarService} from "@gu/components";
import { forkJoin } from 'rxjs';
import {catchError, take} from "rxjs/operators";
import {DocumentenService} from '@gu/services';
import { Zaak } from '@gu/models';

@Component({
  selector: 'gu-features-contezza-document-search',
  templateUrl: './features-contezza-document-search.component.html',
  styleUrls: ['./features-contezza-document-search.component.scss'],
})
export class FeaturesContezzaDocumentSearchComponent implements OnInit, AfterViewInit {
  @Input() zaak: Zaak;
  @Input() mode: string;
  @Input() rootfolder: string;

  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();
  @Output() closeModal: EventEmitter<boolean> = new EventEmitter<boolean>();

  @ViewChild('wrapper', { static: false })
  wrapper: ElementRef;

  readonly errorMessage = 'Er is een fout opgetreden bij het ophalen van documenten.';

  /**
   * Constructor method.
   * @param {Renderer2} renderer2
   * @param {Document} document
   * @param {DocumentenService} documentService
   * @param {SnackbarService} snackbarService
   */
  constructor(private renderer2: Renderer2, @Inject(DOCUMENT) private document: Document, private documentService: DocumentenService, private snackbarService: SnackbarService,) {}

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
   ngOnInit() {

    localStorage.setItem('zaakidentificatie', this.zaak.bronorganisatie);
    localStorage.setItem('zaaknummer', this.zaak.identificatie);

    const script = this.renderer2.createElement('script');
     script.src = '/ui/assets/contezza-zac-doclib.js';
     this.renderer2.appendChild(this.document.body, script);
   }


  /**
   * A lifecycle hook that is called after Angular has fully initialized a component's view. Define an ngAfterViewInit()
   * method to handle any additional initialization tasks.
   */
   ngAfterViewInit() {
     if(!this.wrapper?.nativeElement) {
       return;
     }

      const cdl = this.renderer2.createElement('contezza-zac-doclib');
      cdl.setAttribute('bronorganisatie', this.zaak.bronorganisatie);
      cdl.setAttribute('mode', 'search');
      cdl.setAttribute('zaaktypeurl', this.zaak.zaaktype.url);

      this.renderer2.appendChild(this.wrapper.nativeElement, cdl);

      cdl.addEventListener('documentsUrls', this.addDocuments.bind(this));
   }

   private addDocuments(event: any) {
        const urls: Array<string> = event.detail;

        if (urls?.length) {
          console.log(urls)
          const batch: Array<Observable<any>> = [];

          urls.forEach((url) => {
            const formData = new FormData();

            formData.append("zaak", this.zaak.url);
            formData.append("url", url);

            batch.push(this.documentService.postDocument(formData)
              .pipe(
                catchError((error) => {
                  this.reportError(error);
                  return of(undefined);
                })
              ))
          });

          forkJoin(batch).pipe(take(1)).subscribe((response) => {
            if (response) {
              this.reload.emit(true);
              this.closeModal.emit(true);
            }
          })
        }
    }

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }
}

