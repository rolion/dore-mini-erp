import { TestBed } from '@angular/core/testing';
import { NgbModal, NgbModalRef } from '@ng-bootstrap/ng-bootstrap';

import { CustomerQuickCreateComponent } from '../components/customer-quick-create/customer-quick-create.component';
import { makeCustomer } from '../testing/customer-fixtures';
import { CustomerQuickCreateService } from './customer-quick-create.service';

describe('CustomerQuickCreateService', () => {
  let service: CustomerQuickCreateService;
  let modal: jasmine.SpyObj<NgbModal>;

  function refWith(result: Promise<unknown>): NgbModalRef {
    return { result } as unknown as NgbModalRef;
  }

  beforeEach(() => {
    modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    TestBed.configureTestingModule({ providers: [{ provide: NgbModal, useValue: modal }] });
    service = TestBed.inject(CustomerQuickCreateService);
  });

  it('opens the quick-create modal centered and resolves with the created customer (AC-27)', async () => {
    const customer = makeCustomer({ id: 'c-5' });
    modal.open.and.returnValue(refWith(Promise.resolve(customer)));
    await expectAsync(service.open()).toBeResolvedTo(customer);
    expect(modal.open).toHaveBeenCalledOnceWith(CustomerQuickCreateComponent, { centered: true });
  });

  it('resolves with null when the modal is dismissed (AC-27)', async () => {
    modal.open.and.returnValue(refWith(Promise.reject('cerrar')));
    await expectAsync(service.open()).toBeResolvedTo(null);
  });
});
