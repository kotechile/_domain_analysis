import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { MarketplaceComponent } from './marketplace';

describe('MarketplaceComponent', () => {
  let component: MarketplaceComponent;
  let fixture: ComponentFixture<MarketplaceComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MarketplaceComponent, HttpClientTestingModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MarketplaceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize filter signals', () => {
    expect(component.searchText()).toBe('');
    expect(component.keyword()).toBe('');
    expect(component.minPrice()).toBeNull();
    expect(component.maxPrice()).toBeNull();
    expect(component.preferredOnly()).toBe(false);
  });

  it('should update activeFilterCount with new filters', () => {
    expect(component.activeFilterCount()).toBe(0);
    component.keyword.set('crypto');
    expect(component.activeFilterCount()).toBe(1);
    component.minPrice.set(10);
    expect(component.activeFilterCount()).toBe(2);
    component.keyword.set('');
    component.minPrice.set(null);
    expect(component.activeFilterCount()).toBe(0);
  });

  it('should clear keyword', () => {
    component.keyword.set('crypto');
    component.clearKeyword();
    expect(component.keyword()).toBe('');
  });

  it('should reset all filters including new ones', () => {
    component.keyword.set('crypto');
    component.minPrice.set(10);
    component.maxPrice.set(500);
    component.resetFilters();
    expect(component.keyword()).toBe('');
    expect(component.minPrice()).toBeNull();
    expect(component.maxPrice()).toBeNull();
  });
});
