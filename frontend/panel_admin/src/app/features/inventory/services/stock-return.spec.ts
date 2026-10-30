import { convertToParamMap } from '@angular/router';
import { stockReturnLink } from './stock-return';

const P = '11111111-1111-4111-8111-111111111111';
const W = '22222222-2222-4222-8222-222222222222';

describe('stockReturnLink', () => {
  it('builds the detail link only for return=stock with valid ids (AC-06)', () => {
    const query = convertToParamMap({ return: 'stock', product_id: P, warehouse_id: W });
    expect(stockReturnLink(query)).toEqual(['/pocketbiz/inventory/stock', P, W]);
  });

  it('ignores other return values, free URLs and invalid ids (EDGE-05)', () => {
    expect(stockReturnLink(convertToParamMap({ product_id: P, warehouse_id: W }))).toBeNull();
    expect(stockReturnLink(convertToParamMap({ return: 'https://evil.example', product_id: P, warehouse_id: W }))).toBeNull();
    expect(stockReturnLink(convertToParamMap({ return: 'stock', product_id: 'p-1', warehouse_id: W }))).toBeNull();
    expect(stockReturnLink(convertToParamMap({ return: 'stock', product_id: P }))).toBeNull();
  });
});
