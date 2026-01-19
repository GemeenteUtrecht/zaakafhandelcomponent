import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FeaturesKownslComponent } from './features-kownsl.component';

describe('FeaturesKownslComponent', () => {
  let component: FeaturesKownslComponent;
  let fixture: ComponentFixture<FeaturesKownslComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ FeaturesKownslComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(FeaturesKownslComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
