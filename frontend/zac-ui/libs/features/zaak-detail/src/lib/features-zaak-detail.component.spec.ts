import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FeaturesZaakDetailComponent } from './features-zaak-detail.component';

describe('FeaturesZaakDetailComponent', () => {
  let component: FeaturesZaakDetailComponent;
  let fixture: ComponentFixture<FeaturesZaakDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ FeaturesZaakDetailComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(FeaturesZaakDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
