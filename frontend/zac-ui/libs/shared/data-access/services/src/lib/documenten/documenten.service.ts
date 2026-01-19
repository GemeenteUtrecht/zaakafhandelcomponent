import {Injectable} from '@angular/core';
import {Observable} from 'rxjs';
import {
  Document,
  ExtensiveCell,
  InformatieObjectType,
  MetaConfidentiality,
  ReadWriteDocument,
  RowData,
  Table,
  Zaak
} from '@gu/models';
import { ApplicationHttpClient, IRequestOptions } from '@gu/services';
import {HttpHeaders} from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class DocumentenService {

  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * Get documents for an activity.
   * @param {string} documentUrl
   * @returns {Observable<Document>}
   */
  getDocument(documentUrl: string): Observable<Document> {
    const endpoint = encodeURI(`/core/api/documents/info?document=${documentUrl}`);
    return this.http.Get<Document>(endpoint);
  }

  /**
   * Reads a document.
   * @param readUrl
   */
  readDocument(readUrl: string): Observable<ReadWriteDocument> {
    const endpoint = encodeURI(readUrl);
    return this.http.Post<ReadWriteDocument>(endpoint);
  }

  openDocumentEdit(writeUrl: string, zaak: string): Observable<ReadWriteDocument> {
    const endpoint = encodeURI(writeUrl);
    const formData = { zaak };
    return this.http.Post<ReadWriteDocument>(endpoint, formData);
  }

  closeDocumentEdit(deleteUrl: string): Observable<any> {
    const endpoint = encodeURI(deleteUrl);
    return this.http.Delete<any>(endpoint);
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

  getDocumentTypes(mainZaakUrl): Observable<InformatieObjectType[]> {
    const endpoint = encodeURI(`/api/core/informatieobjecttypen?zaak=${mainZaakUrl}`);
    return this.http.Get<InformatieObjectType[]>(endpoint);
  }

  /**
   * Format the layout of the table.
   * @param data
   * @param tableHead
   * @param {Zaak} zaak
   * @param {MetaConfidentiality[]} metaConfidentialities
   * @param {Function} onChange onChange callback.
   * @returns {Table}
   */
  formatTableData(data, tableHead, zaak: Zaak, metaConfidentialities: MetaConfidentiality[], onChange: Function): Table {
    const tableData: Table = new Table(tableHead, []);

    tableData.bodyData = data.map((element: Document) => {
      // The "locked" and "currentUserIsEditing" states decide if certain buttons should be shown in the table or not.
      // If a case is closed (when "zaak.resultaat" is available) and the user is not allowed to force edit ("zaak.kanGeforceerdBijwerken),
      // the buttons will also be hidden.
      const icon = (element.locked && !element.currentUserIsEditing) ? 'lock' : 'lock_open'
      const iconColor = (element.locked && !element.currentUserIsEditing) ? 'orange' : 'green'
      const iconInfo = (element.locked && !element.currentUserIsEditing) ? `Het document wordt al door "${element.lockedBy}" bewerkt.` : 'U kunt het document bewerken. Klik op "Bewerkingen opslaan" na het bewerken.'
      const editLabel = element.currentUserIsEditing ? 'Bewerkingen opslaan' : 'Bewerken';
      const editUrl = element.currentUserIsEditing ? element.deleteUrl : element.writeUrl;
      const editButtonStyle = element.currentUserIsEditing ? 'primary' : 'tertiary';

      const showEditCell = (((!element.locked || element.currentUserIsEditing) && !zaak.resultaat) || (!zaak.resultaat && zaak.kanGeforceerdBijwerken)) && element.writeUrl;
      const showOverwriteCell = !element.locked && !zaak.resultaat;

      let readOrDownloadCell;
      const isDownloadCell = (element.titel.toLowerCase().split('.')[1] === ('msg' || 'pdf')) || (element.readUrl.length === 0 && element.downloadUrl.length > 0)
      const readCell = {
        type: 'button',
        style: 'no-minwidth',
        label: 'Lezen',
        value: element.readUrl,
      }
      const downloadCell = {
        type: 'link',
        style: 'no-minwidth',
        label: 'Downloaden',
        url: element.downloadUrl,
      }
      if (isDownloadCell) {
        readOrDownloadCell = downloadCell;
      } else {
        readOrDownloadCell = readCell;
      }

      const editCell: ExtensiveCell = {
        type: 'button',
        style: 'no-minwidth',
        label: editLabel,
        value: editUrl,
        buttonType: editButtonStyle
      };
      const overwriteCell: ExtensiveCell = {
        type: 'button',
        style: 'no-minwidth',
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
          versie: {
            type: 'text',
            style: 'no-minwidth',
            label: String(element.versie)
          },
          lezen: readOrDownloadCell,
          bewerken: showEditCell ? editCell : '',
          overschrijven: showOverwriteCell ? overwriteCell : '',
          auteur: element.auteur,
          type: element.informatieobjecttype['omschrijving'],
          vertrouwelijkheidaanduiding: {
            choices: metaConfidentialities,
            type: (element.currentUserIsEditing) ? 'text' :'select',
            label: element.vertrouwelijkheidaanduiding,
            value: metaConfidentialities.find((metaConfidentiality: MetaConfidentiality) => metaConfidentiality.value === element.vertrouwelijkheidaanduiding),
            onChange: (choice) => {onChange(element, choice)}
          },
        }
      }
      return cellData;
    })

    return tableData
  }
}
