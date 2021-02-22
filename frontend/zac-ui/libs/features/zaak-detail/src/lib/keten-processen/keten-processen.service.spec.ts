import { TestBed } from '@angular/core/testing';

import { KetenProcessenService } from './keten-processen.service';

describe('KetenProcessenService', () => {
  let service: KetenProcessenService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(KetenProcessenService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
