import { Injectable } from '@angular/core';
import {
  HttpErrorResponse,
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
} from '@angular/common/http';
import { Observable, throwError, timer } from 'rxjs';
import { mergeMap, retryWhen } from 'rxjs/operators';

/**
 * Retries failed GET requests on 502, 503, or 504 with exponential backoff
 * (1s, 3s, 6s). Non-GET requests and other error codes are not retried.
 */
@Injectable()
export class RetryInterceptor implements HttpInterceptor {

  private static readonly RETRY_DELAYS = [1000, 3000, 6000];
  private static readonly RETRY_STATUS_CODES = [502, 503, 504];

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    if (req.method !== 'GET') {
      return next.handle(req);
    }

    return next.handle(req).pipe(
      retryWhen(errors =>
        errors.pipe(
          mergeMap((error, attempt) => {
            if (
              error instanceof HttpErrorResponse &&
              RetryInterceptor.RETRY_STATUS_CODES.includes(error.status) &&
              attempt < RetryInterceptor.RETRY_DELAYS.length
            ) {
              return timer(RetryInterceptor.RETRY_DELAYS[attempt]);
            }
            return throwError(error);
          })
        )
      )
    );
  }
}
