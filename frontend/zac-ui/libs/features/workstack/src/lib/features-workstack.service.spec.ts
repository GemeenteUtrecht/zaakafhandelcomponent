import { TestBed } from '@angular/core/testing';

import { FeaturesWorkstackService } from './features-workstack.service';

describe('FeaturesWorkstackService', () => {
  let service: FeaturesWorkstackService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(FeaturesWorkstackService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
