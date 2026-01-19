import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AdviserenAccorderenComponent } from './adviseren-accorderen.component';

describe('AdviserenAccorderenComponent', () => {
  let component: AdviserenAccorderenComponent;
  let fixture: ComponentFixture<AdviserenAccorderenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ AdviserenAccorderenComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(AdviserenAccorderenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
