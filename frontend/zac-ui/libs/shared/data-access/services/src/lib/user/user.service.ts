import {Injectable} from '@angular/core';
import {HttpResponse} from '@angular/common/http';
import {Observable, Subscriber} from 'rxjs';
import {User} from '@gu/models';
import {ApplicationHttpClient} from '@gu/services';
import {CachedObservableMethod, ClearCacheOnMethodCall} from '@gu/utils';


@Injectable({
  providedIn: 'root'
})
export class UserService {
  constructor(private http: ApplicationHttpClient) {
  }

  /**
   * Retrieves the current user and whether this user is a hijacked user.
   * @return {Observable} Results in array: [User, isHijacked].
   */
  @CachedObservableMethod('UserService.getCurrentUser')
  getCurrentUser(): Observable<[User, boolean]> {
    return new Observable((subscriber: Subscriber<[User, boolean]>) => {
      const endpoint = encodeURI('/api/accounts/users/me');

      this.http.Get<HttpResponse<User>>(endpoint, {observe: 'response'}).subscribe(
        (response) => {
          const {headers, body} = response;
          const isHijacked = JSON.parse(headers.get('X-Is-Hijacked'));
          subscriber.next([body, isHijacked]);
        },
        subscriber.error
      );
    });
  }

  /**
   * Releases the current user.
   * @return {Observable}
   */
  @ClearCacheOnMethodCall('UserService.getCurrentUser')
  releaseHijack(): Observable<any> {
    const endpoint = encodeURI(`/accounts/hijack/release/`);
    return this.http.Post<any>(endpoint, {}, {responseType: 'text'});
  }

  /**
   * Logs user out.
   * @returns {Observable}
   */
  logOutUser(): Observable<any> {
    const endpoint = encodeURI(`/api/accounts/logout`);
    return this.http.Post<any>(endpoint);
  }

  /**
   * Returns the string representation for a user.
   * @param {User} user
   * @return {string}
   */
  stringifyUser(user: User): string {
    if(!user) {
      return '-';
    }

    return user.firstName
      ? `${user.firstName} ${user.lastName}`.trim()
      : user.username;
  }
}
