import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ZaakDetailComponent } from './zaak-detail.component';

describe('ZaakDetailComponent', () => {
  let component: ZaakDetailComponent;
  let fixture: ComponentFixture<ZaakDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ZaakDetailComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ZaakDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
