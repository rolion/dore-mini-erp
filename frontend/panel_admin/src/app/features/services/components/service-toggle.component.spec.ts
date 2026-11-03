import { provideTestTranslations } from '../../../core/i18n/testing';
import { TestBed } from '@angular/core/testing';
import { Subject } from 'rxjs';
import Swal from 'sweetalert2';
import { CatalogService } from '../models/service';
import { ServicesApiService } from '../services/services-api.service';
import { ServiceToggleComponent } from './service-toggle.component';

describe('ServiceToggleComponent', () => {
  it('requires confirmation, prevents duplicate actions and emits the updated service', async () => {
    const service: CatalogService = { id: 'one', name: 'Consulta', code: '', description: '', basePrice: '120.00',
      durationMinutes: 30, specialtyId: null, specialtyName: null, active: true, createdAt: '', updatedAt: '' };
    const response = new Subject<CatalogService>();
    const api = jasmine.createSpyObj<ServicesApiService>('api', ['setActive']); api.setActive.and.returnValue(response);
    TestBed.configureTestingModule({ imports: [ServiceToggleComponent], providers: [...provideTestTranslations(), { provide: ServicesApiService, useValue: api }] });
    const fixture = TestBed.createComponent(ServiceToggleComponent); fixture.componentRef.setInput('service', service);
    const c = fixture.componentInstance; const updated = spyOn(c.updated, 'emit');
    const confirm = spyOn(Swal, 'fire').and.resolveTo({ isConfirmed: false, isDenied: false, isDismissed: true });
    await c.toggle(); expect(api.setActive).not.toHaveBeenCalled(); expect(c.busy).toBeFalse();
    confirm.and.resolveTo({ isConfirmed: true, isDenied: false, isDismissed: false });
    await c.toggle(); await c.toggle(); expect(api.setActive).toHaveBeenCalledOnceWith('one', false);
    response.next({ ...service, active: false }); response.complete();
    expect(updated).toHaveBeenCalledWith({ ...service, active: false }); expect(c.busy).toBeFalse();
  });
});
