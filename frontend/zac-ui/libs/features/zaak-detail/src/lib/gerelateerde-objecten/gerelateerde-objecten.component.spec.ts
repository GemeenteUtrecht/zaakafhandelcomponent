import { ComponentFixture, TestBed } from '@angular/core/testing';

import { GerelateerdeObjectenComponent } from './gerelateerde-objecten.component';

describe('GerelateerdeObjectenComponent', () => {
  let component: GerelateerdeObjectenComponent;
  let fixture: ComponentFixture<GerelateerdeObjectenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ GerelateerdeObjectenComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(GerelateerdeObjectenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
