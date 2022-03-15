import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DeleteAuthProfileComponent } from './delete-auth-profile.component';

describe('DeleteAuthProfileComponent', () => {
  let component: DeleteAuthProfileComponent;
  let fixture: ComponentFixture<DeleteAuthProfileComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ DeleteAuthProfileComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(DeleteAuthProfileComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
