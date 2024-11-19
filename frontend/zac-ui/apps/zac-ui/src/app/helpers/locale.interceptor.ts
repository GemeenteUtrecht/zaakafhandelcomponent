import {Injectable} from '@angular/core';
import {
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
} from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable()
export class LocaleInterceptor implements HttpInterceptor {  
    intercept(
      req: HttpRequest<any>,
      next: HttpHandler
    ): Observable<HttpEvent<any>> {    
      const request = req.clone({
        setHeaders: { "Accept-Language": 'nl-NL;q=0.9,en-US,en;q=0.8' }
      });
  
      return next.handle(request);
    }
  }