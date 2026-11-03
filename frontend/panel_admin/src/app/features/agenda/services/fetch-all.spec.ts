import { of } from 'rxjs';
import { Page } from '../../../shared/models/page';
import { fetchAll } from './fetch-all';

describe('fetchAll', () => {
  it('concatenates every page until there is no next one', () => {
    const pages: Record<number, Page<number>> = {
      1: { count: 3, next: 'x', previous: null, results: [1, 2] },
      2: { count: 3, next: null, previous: 'x', results: [3] },
    };
    const requested: number[] = [];
    let values: number[] = [];
    fetchAll(page => { requested.push(page); return of(pages[page]); }).subscribe(all => values = all);
    expect(values).toEqual([1, 2, 3]);
    expect(requested).toEqual([1, 2]);
  });
});
