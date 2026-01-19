import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FeaturesSearchComponent } from './features-search.component';

describe('FeaturesSearchComponent', () => {
  let component: FeaturesSearchComponent;
  let fixture: ComponentFixture<FeaturesSearchComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ FeaturesSearchComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(FeaturesSearchComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
