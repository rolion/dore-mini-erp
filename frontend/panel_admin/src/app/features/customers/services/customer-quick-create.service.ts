import { Injectable, inject } from '@angular/core';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { CustomerQuickCreateComponent } from '../components/customer-quick-create/customer-quick-create.component';
import { Customer } from '../models/customer';

/** Abre el modal de creación rápida de cliente; usado desde el formulario de pedido (REQ-CUS-001, criterio 2). */
@Injectable({
  providedIn: 'root',
})
export class CustomerQuickCreateService {
  private modal = inject(NgbModal);

  /** Devuelve el cliente creado, o `null` si el usuario cerró el modal sin guardar. */
  open(): Promise<Customer | null> {
    const ref = this.modal.open(CustomerQuickCreateComponent, { centered: true });
    return ref.result.then(
      (customer: Customer) => customer,
      () => null,
    );
  }
}
