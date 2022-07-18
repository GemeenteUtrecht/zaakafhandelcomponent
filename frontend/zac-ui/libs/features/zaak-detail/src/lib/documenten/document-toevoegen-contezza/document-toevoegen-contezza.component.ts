import { AfterContentInit, Component, EventEmitter, Input, OnInit, Output, ViewEncapsulation } from '@angular/core';
import { Zaak } from '@gu/models';
import { ActivatedRoute, Router } from '@angular/router';

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
export class DocumentToevoegenContezzaComponent implements AfterContentInit {
  @Input() zaak: Zaak;

  @Output() reload = new EventEmitter<boolean>();
  @Output() closeModal = new EventEmitter<boolean>();

  tabIndex = 0;

  constructor(
    private activatedRoute: ActivatedRoute,
    private router: Router,
  ) {
  }

  ngAfterContentInit() {
    this.handleQueryParam();
  }

  /**
   * Open modal according to query param
   */
  handleQueryParam() {
    this.activatedRoute.queryParams.subscribe(queryParams => {
      const tabParam = queryParams['tab'];
      if (tabParam) {
        this.tabIndex = tabParam;
      }
    });
  }

  setQueryParam(event) {
    this.router.navigate(
      [],
      {
        relativeTo: this.activatedRoute,
        queryParams: { tab: event.index },
        queryParamsHandling: 'merge'
      }
    );
  }

}
