import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { ProductUsesComponent } from './product-uses.component';
import { productUses } from './product-uses';

describe('productUses', () => {
  it('derives insumo from raw material, packaging and intermediate only (AC-02)', () => {
    for (const category of ['raw_material', 'packaging', 'intermediate']) {
      expect(productUses({ canSell: false, canBuy: false, category })).toEqual(['ingredient']);
    }
    for (const category of ['finished', 'merchandise', null, '']) {
      expect(productUses({ canSell: false, canBuy: false, category })).toEqual([]);
    }
  });

  it('combines uses in a fixed order (AC-02)', () => {
    expect(productUses({ canSell: true, canBuy: true, category: 'raw_material' })).toEqual(['sell', 'buy', 'ingredient']);
  });
});

describe('ProductUsesComponent', () => {
  function render(product: { canSell: boolean; canBuy: boolean; category: string | null }): string {
    TestBed.configureTestingModule({ providers: [provideTestTranslations()] });
    const fixture = TestBed.createComponent(ProductUsesComponent);
    fixture.componentRef.setInput('product', product);
    fixture.detectChanges();
    return (fixture.nativeElement as HTMLElement).textContent ?? '';
  }

  it('shows text chips for every use (AC-01)', () => {
    const text = render({ canSell: true, canBuy: true, category: 'raw_material' });
    expect(text).toContain('Vendible');
    expect(text).toContain('Comprable');
    expect(text).toContain('Insumo');
  });

  it('shows «Sin usos» when none applies (EDGE-02)', () => {
    expect(render({ canSell: false, canBuy: false, category: 'finished' })).toContain('Sin usos');
  });

  it('does not show insumo for a product por revisar (EDGE-01)', () => {
    expect(render({ canSell: true, canBuy: false, category: null })).not.toContain('Insumo');
  });
});
