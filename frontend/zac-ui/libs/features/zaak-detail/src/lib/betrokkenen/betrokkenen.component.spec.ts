import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BetrokkenenComponent } from './betrokkenen.component';

describe('BetrokkenenComponent', () => {
  let component: BetrokkenenComponent;
  let fixture: ComponentFixture<BetrokkenenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ BetrokkenenComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(BetrokkenenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
