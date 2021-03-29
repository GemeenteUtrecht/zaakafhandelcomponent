import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ToegangVerlenenComponent } from './toegang-verlenen.component';

describe('ToegangVerlenenComponent', () => {
  let component: ToegangVerlenenComponent;
  let fixture: ComponentFixture<ToegangVerlenenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ToegangVerlenenComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ToegangVerlenenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
