import { ComponentFixture, TestBed } from '@angular/core/testing';

import { GerelateerdeZakenComponent } from './gerelateerde-zaken.component';

describe('GerelateerdeZakenComponent', () => {
  let component: GerelateerdeZakenComponent;
  let fixture: ComponentFixture<GerelateerdeZakenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ GerelateerdeZakenComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(GerelateerdeZakenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
