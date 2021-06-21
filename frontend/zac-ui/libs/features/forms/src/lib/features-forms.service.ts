import {Injectable} from '@angular/core';
import {ApplicationHttpClient} from '@gu/services';
import {Observable} from 'rxjs';
import {Form} from './features-forms.model';
import {environment} from "../environments/environment";


@Injectable({
  providedIn: 'root'
})
export class FeaturesFormsService {

  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * Request the forms API.
   */
  getForms(): Observable<Form[]> {
    const endpoint = encodeURI(`/api/forms`);
    return this.http.Get<Form[]>(endpoint);
  }

  /**
   * Returns the URL of a form based on it's slug and whether to use a test environment.
   * A test environment is assumed when the current window's location matches 'test' or 'localhost'.
   * @param {Form} form
   * @return {string}
   */
  getAbsoluteFormURL(form: Form): string {
    const scheme = 'https://'
    const hostname = environment.openFormsHostname;
    return `${scheme}${hostname}/forms/${form.slug}/`;
  }
}
