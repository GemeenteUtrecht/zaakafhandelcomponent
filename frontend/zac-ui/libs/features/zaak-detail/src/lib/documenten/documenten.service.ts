import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Document, ExtensiveCell, ReadWriteDocument, RowData, Table } from '@gu/models';
import { ApplicationHttpClient } from '@gu/services';
import {CachedObservableMethod} from '@gu/utils';
import {HttpParams, HttpResponse} from '@angular/common/http';
import {doc} from 'prettier';

@Injectable({
  providedIn: 'root'
})
export class DocumentenService {

  constructor(private http: ApplicationHttpClient) { }

  readDocument(readUrl: string): Observable<ReadWriteDocument> {
    const endpoint = encodeURI(readUrl);
    return this.http.Post<ReadWriteDocument>(endpoint);
  }

  openDocumentEdit(writeUrl: string): Observable<ReadWriteDocument> {
    const endpoint = encodeURI(writeUrl);
    return this.http.Post<ReadWriteDocument>(endpoint);
  }

  closeDocumentEdit(deleteUrl: string): Observable<any> {
    const endpoint = encodeURI(deleteUrl);
    return this.http.Delete<any>(endpoint);
  }

  getConfidentiality(): Observable<any> {
    const endpoint = encodeURI("/api/core/vertrouwelijkheidsaanduidingen");
    return this.http.Get<any>(endpoint);
  }

  setConfidentiality(documentUrl: string, confidentiality: 'openbaar' | 'beperkt_openbaar' | 'intern' | 'zaakvertrouwelijk' | 'vertrouwelijk' | 'confidentieel' | 'geheim' | 'zeer_geheim', reason: string, zaakUrl: string): Observable<Document> {
    const endpoint = encodeURI('/api/core/cases/document');
    const formData = new FormData()
    formData.append('reden', reason);
    formData.append('url', documentUrl);
    formData.append('vertrouwelijkheidaanduiding', confidentiality);
    formData.append('zaak', zaakUrl);
    return this.http.Patch<Document>(endpoint, formData)
  }

  postDocument(formData: FormData): Observable<Document> {
    return this.http.Post<any>(encodeURI(`/api/core/cases/document`), formData);
  }

  patchDocument(formData: FormData): Observable<any> {
    return this.http.Patch<any>(encodeURI(`/api/core/cases/document`), formData);
  }

  getDocumentTypes(mainZaakUrl): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/api/core/document-types?zaak=${mainZaakUrl}`);
    return this.http.Get<any>(endpoint);
  }

  /**
   * Format the layout of the table.
   * @param data
   * @param tableHead
   * @returns {Table}
   */
  formatTableData(data, tableHead): Table {
    const tableData: Table = new Table(tableHead, []);

    tableData.bodyData = data.map( (element: Document) => {
      // The "locked" and "currentUserIsEditing" states decide if certain buttons should be shown in the table or not.
      const icon = (element.locked && !element.currentUserIsEditing) ? 'lock' : 'lock_open'
      const iconColor = (element.locked && !element.currentUserIsEditing) ? 'orange' : 'green'
      const iconInfo = (element.locked && !element.currentUserIsEditing) ? 'Het document wordt al door een ander persoon bewerkt.' : 'U kunt het document bewerken. Klik op "Bewerkingen opslaan" na het bewerken.'
      const editLabel = element.currentUserIsEditing ? 'Bewerkingen opslaan' : 'Bewerken';
      const editButtonStyle = element.currentUserIsEditing  ? 'primary' : 'tertiary';
      const showEditCell = !element.locked || element.currentUserIsEditing;
      const editCell: ExtensiveCell = {
        type: 'button',
        label: editLabel,
        value: element.writeUrl,
        buttonType: editButtonStyle
      };
      const overwriteCell: ExtensiveCell = {
        type: 'button',
        label: 'Overschrijven',
        value: element.url,
        buttonInfo: 'Met deze knop kan je een oud document vervangen door een nieuw document'
      };
      const docNameButton: ExtensiveCell | string = element.locked ? element.titel : {
        type: 'button',
        label: element.titel,
        value: element,
        sortValue: element.titel
      }
      const cellData: RowData = {
        cellData: {
          opSlot: {
            type: 'icon',
            label: icon,
            iconColor: iconColor,
            iconInfo: iconInfo
          },
          bestandsnaam: docNameButton,
          versie: String(element.versie),
          lezen: {
            type: 'button',
            label: 'Lezen',
            value: element.readUrl
          },
          bewerken: showEditCell ? editCell : '',
          overschrijven: element.locked ? '' : overwriteCell,
          auteur: element.auteur,
          type: element.informatieobjecttype['omschrijving'],
        }
      }
      return cellData;
    })

    return tableData
  }
}
