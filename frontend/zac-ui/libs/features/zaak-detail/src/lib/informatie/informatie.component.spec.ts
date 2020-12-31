import { ComponentFixture, TestBed } from '@angular/core/testing';

import { InformatieComponent } from './informatie.component';

describe('InformatieComponent', () => {
  let component: InformatieComponent;
  let fixture: ComponentFixture<InformatieComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ InformatieComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(InformatieComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
