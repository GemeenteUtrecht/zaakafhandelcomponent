import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RelatieToevoegenComponent } from './relatie-toevoegen.component';

describe('RelatieToevoegenComponent', () => {
  let component: RelatieToevoegenComponent;
  let fixture: ComponentFixture<RelatieToevoegenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ RelatieToevoegenComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(RelatieToevoegenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
