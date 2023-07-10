import {Injectable} from '@angular/core';
import {ApplicationHttpClient} from '@gu/services';
import {Observable} from 'rxjs';
import {Checklist, ChecklistAnswer, ChecklistType} from '@gu/models';


@Injectable({
  providedIn: 'root'
})
export class ChecklistService {
  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * Retrieve checklisttype and related questions.
   * @return {Observable<ChecklistType[]>}
   */
  retrieveChecklistTypeAndRelatedQuestions(bronorganisatie: string, identificatie: string): Observable<ChecklistType> {
    const endpoint = encodeURI(`/api/checklists/zaak-checklisttypes/${bronorganisatie}/${identificatie}`);

    return this.http.Get<ChecklistType>(endpoint);
  }

  /**
   * Retrieve checklist and related answers.
   * @return {Observable<Checklist[]>}
   */
  retrieveChecklistAndRelatedAnswers(bronorganisatie: string, identificatie: string): Observable<Checklist> {
    const endpoint = encodeURI(`/api/checklists/zaak-checklists/${bronorganisatie}/${identificatie}`);
    return this.http.Get<Checklist>(endpoint);
  }

  /**
   * Create checklist and related answers.
   * FIXME: Zaak should not be necessary?
   */
  createChecklistAndRelatedAnswers(bronorganisatie: string, identificatie: string, checklistAnswers: ChecklistAnswer[]): Observable<Checklist> {
    const endpoint = encodeURI(`/api/checklists/zaak-checklists/${bronorganisatie}/${identificatie}`);

    const params = {
      answers: checklistAnswers,
    }

    return this.http.Post<Checklist>(endpoint, params);
  }

  /**
   * Update checklist and related answers.
   * FIXME: Zaak should not be necessary?
   */
  updateChecklistAndRelatedAnswers(bronorganisatie: string, identificatie: string, checklistAnswers: ChecklistAnswer[]): Observable<Checklist> {
    const endpoint = encodeURI(`/api/checklists/zaak-checklists/${bronorganisatie}/${identificatie}`);

    const params = {
      answers: checklistAnswers,
    }

    return this.http.Put<Checklist>(endpoint, params);
  }

  /**
   * Lock checklist.
   * @param {string} bronorganisatie
   * @param {string} identificatie
   */
  lockChecklist(bronorganisatie: string, identificatie: string){
    const endpoint = encodeURI(`/api/checklists/zaak-checklists/${bronorganisatie}/${identificatie}/lock`);
    return this.http.Post<any>(endpoint);
  }

  /**
   * Unlock checklist
   * @param {string} bronorganisatie
   * @param {string} identificatie
   */
  unLockChecklist(bronorganisatie: string, identificatie: string){
    const endpoint = encodeURI(`/api/checklists/zaak-checklists/${bronorganisatie}/${identificatie}/unlock`);
    return this.http.Post<any>(endpoint);
  }
}
