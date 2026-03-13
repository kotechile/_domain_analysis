import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ThemeShowcase } from './theme-showcase';

describe('ThemeShowcase', () => {
  let component: ThemeShowcase;
  let fixture: ComponentFixture<ThemeShowcase>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ThemeShowcase],
    }).compileComponents();

    fixture = TestBed.createComponent(ThemeShowcase);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
