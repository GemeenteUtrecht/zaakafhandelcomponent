import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Document, ExtensiveCell, ReadWriteDocument, RowData, Table } from '@gu/models';
import { ApplicationHttpClient } from '@gu/services';
import {CachedObservableMethod} from '@gu/utils';

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
      const confidentialityButton: ExtensiveCell | string = element.locked ? element.vertrouwelijkheidaanduiding : {
        type: 'button',
        label: element.vertrouwelijkheidaanduiding,
        value: element
      }
      const cellData: RowData = {
        cellData: {
          opSlot: {
            type: 'icon',
            label: icon,
            iconColor: iconColor,
            iconInfo: iconInfo
          },
          bestandsnaam: element.bestandsnaam,
          versie: String(element.versie),
          lezen: {
            type: 'button',
            label: 'Lezen',
            value: element.readUrl
          },
          bewerken: showEditCell ? editCell : '',
          overschrijven: element.locked ? '' : overwriteCell,
          type: element.informatieobjecttype['omschrijving'],
          vertrouwelijkheid: confidentialityButton
        }
      }
      return cellData;
    })

    return tableData
  }
}
