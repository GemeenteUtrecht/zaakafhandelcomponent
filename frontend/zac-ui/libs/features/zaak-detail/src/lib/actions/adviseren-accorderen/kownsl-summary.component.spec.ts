import { ComponentFixture, TestBed } from '@angular/core/testing';

import { KownslSummaryComponent } from './kownsl-summary.component';

describe('KownslSummaryComponent', () => {
  let component: KownslSummaryComponent;
  let fixture: ComponentFixture<KownslSummaryComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ KownslSummaryComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(KownslSummaryComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
