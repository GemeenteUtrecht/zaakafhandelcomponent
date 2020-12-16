import {TestBed} from '@angular/core/testing';

import {ApplicationHttpClient} from './http-client';
import {HttpClientTestingModule} from '@angular/common/http/testing';

describe('HttpClientService', () => {
  beforeEach(() => TestBed.configureTestingModule({
    imports: [
      HttpClientTestingModule
    ]
  }));

  it('should be created', () => {
    const service: ApplicationHttpClient = TestBed.get(ApplicationHttpClient);
    expect(service).toBeTruthy();
  });
});
