import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ZakenComponent } from './zaken.component';

describe('ZakenComponent', () => {
  let component: ZakenComponent;
  let fixture: ComponentFixture<ZakenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ZakenComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ZakenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
