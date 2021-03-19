import { ComponentFixture, TestBed } from '@angular/core/testing';

import { KownslComponent } from './kownsl.component';

describe('KownslComponent', () => {
  let component: KownslComponent;
  let fixture: ComponentFixture<KownslComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ KownslComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(KownslComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
