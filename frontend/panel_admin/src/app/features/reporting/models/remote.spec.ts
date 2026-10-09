import { Subject, of, throwError } from 'rxjs';
import { Remote, RemoteResource, toRemote } from './remote';

describe('Remote', () => {
  it('goes from loading to ready (AC-25)', () => {
    const states: Remote<number>[] = [];
    toRemote(of(5)).subscribe((s) => states.push(s));
    expect(states.map((s) => s.status)).toEqual(['loading', 'ready']);
    expect(states[1].data).toBe(5);
  });

  it('turns a failure into an error state with its message (AC-25)', () => {
    const states: Remote<number>[] = [];
    toRemote(throwError(() => new Error('No se pudo cargar.'))).subscribe((s) => states.push(s));
    expect(states.map((s) => s.status)).toEqual(['loading', 'error']);
    expect(states[1].error).toBe('No se pudo cargar.');
  });

  it('fetches once for several subscribers and again on reload (AC-25)', () => {
    let calls = 0;
    const resource = new RemoteResource(() => {
      calls++;
      return of(calls);
    });
    const a: Remote<number>[] = [];
    const b: Remote<number>[] = [];
    resource.state$.subscribe((s) => a.push(s));
    resource.state$.subscribe((s) => b.push(s));
    expect(calls).toBe(1);
    resource.reload();
    expect(calls).toBe(2);
    expect(a[a.length - 1].data).toBe(2);
    expect(b[b.length - 1].data).toBe(2);
  });

  it('drops a stale answer when reloaded before it arrives', () => {
    const pending = [new Subject<string>(), new Subject<string>()];
    let index = 0;
    const resource = new RemoteResource(() => pending[index++]);
    let last: Remote<string> | null = null;
    resource.state$.subscribe((s) => (last = s));
    resource.reload();
    pending[0].next('viejo');
    pending[1].next('nuevo');
    expect((last as unknown as Remote<string>).data).toBe('nuevo');
  });
});
