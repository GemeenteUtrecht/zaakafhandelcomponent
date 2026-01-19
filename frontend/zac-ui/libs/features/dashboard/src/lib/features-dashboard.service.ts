import { Injectable } from '@angular/core';
import { ApplicationHttpClient } from '@gu/services';
import { Observable } from 'rxjs';
import { BoardItem, Dashboard } from '@gu/models';

@Injectable({
  providedIn: 'root',
})
export class FeaturesDashboardService {
  constructor(private http: ApplicationHttpClient) {}

  listBoards(): Observable<Dashboard[]> {
    const endpoint = '/api/dashboard/boards';
    return this.http.Get<Dashboard[]>(endpoint);
  }

  getBoardItems(slug): Observable<BoardItem[]> {
    const endpoint = `/api/dashboard/items?board_slug=${slug}`;
    return this.http.Get<BoardItem[]>(endpoint);
  }


  createBoardItem(formData): Observable<BoardItem> {
    const endpoint = `/api/dashboard/items`;
    return this.http.Post<BoardItem>(endpoint, formData);
  }

  updateBoardItem(uuid, formData): Observable<BoardItem> {
    const endpoint = `/api/dashboard/items/${uuid}`;
    return this.http.Put<BoardItem>(endpoint, formData);
  }

  deleteBoardItem(uuid): Observable<BoardItem> {
    const endpoint = `/api/dashboard/items/${uuid}`;
    return this.http.Delete<BoardItem>(endpoint);
  }

}
