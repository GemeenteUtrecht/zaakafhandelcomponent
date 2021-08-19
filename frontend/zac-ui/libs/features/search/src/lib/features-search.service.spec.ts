import { TestBed } from '@angular/core/testing';

import { SearchService } from './features-search.service';

describe('FeaturesSearchService', () => {
  let service: SearchService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(SearchService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
