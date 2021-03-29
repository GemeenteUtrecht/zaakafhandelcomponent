import { Component, OnInit } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { ActivatedRoute, Router } from '@angular/router';
import { Observable } from 'rxjs';
import { Zaak } from '@gu/models';
import { ModalService } from '@gu/components';

@Component({
  selector: 'gu-features-zaak-detail',
  templateUrl: './features-zaak-detail.component.html',
  styleUrls: ['./features-zaak-detail.component.scss']
})
export class FeaturesZaakDetailComponent implements OnInit {
  bronorganisatie: string;
  identificatie: string;
  mainZaakUrl: string;

  zaakData: Zaak;

  isLoading: boolean;
  hasError: boolean;
  errorMessage: string;

  isNotLoggedIn: boolean;
  readonly NOT_LOGGED_IN_MESSAGE = "Authenticatiegegevens zijn niet opgegeven.";

  loginUrl: string;


  constructor(
    private http: ApplicationHttpClient,
    private route: ActivatedRoute,
    private router: Router,
    private modalService: ModalService
  ) { }

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.bronorganisatie = params['bronorganisatie'];
      this.identificatie = params['identificatie'];

      this.fetchInformation();
    });
  }

  fetchInformation() {
    this.isLoading = true;
    this.getInformation().subscribe(data => {
      this.zaakData = data;
      this.mainZaakUrl = data.url ? data.url : null;
      this.isLoading = false;
    }, errorResponse => {
      this.hasError = true;
      this.errorMessage = errorResponse.error.detail;
      if (this.errorMessage === this.NOT_LOGGED_IN_MESSAGE) {
        this.setLoginUrl()
        this.isNotLoggedIn = true;
      }
      this.isLoading = false;
    })
  }

  getInformation(): Observable<Zaak> {
    const endpoint = encodeURI(`/api/core/cases/${this.bronorganisatie}/${this.identificatie}`);
    return this.http.Get<Zaak>(endpoint);
  }

  setLoginUrl(): void {
    const currentPath = this.router.url;
    this.loginUrl = `/accounts/login/?next=/ui${currentPath}`
  }

  openModal(id: string) {
    this.modalService.open(id);
  }

}
