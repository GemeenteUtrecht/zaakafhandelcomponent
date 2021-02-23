import { TestBed } from '@angular/core/testing';

import { FeaturesSearchService } from './features-search.service';

describe('FeaturesSearchService', () => {
  let service: FeaturesSearchService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(FeaturesSearchService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
