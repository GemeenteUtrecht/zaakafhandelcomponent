import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FeaturesReportsComponent } from './features-reports.component';

describe('FeaturesReportsComponent', () => {
  let component: FeaturesReportsComponent;
  let fixture: ComponentFixture<FeaturesReportsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [FeaturesReportsComponent],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(FeaturesReportsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
