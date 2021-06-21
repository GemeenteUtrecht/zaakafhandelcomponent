import { TestBed } from '@angular/core/testing';

import { GerelateerdeObjectenService } from './gerelateerde-objecten.service';

describe('GerelateerdeObjectenService', () => {
  let service: GerelateerdeObjectenService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(GerelateerdeObjectenService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
