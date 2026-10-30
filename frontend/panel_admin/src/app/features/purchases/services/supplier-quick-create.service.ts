import { Injectable, inject } from '@angular/core';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { SupplierQuickCreateComponent } from '../components/supplier-quick-create/supplier-quick-create.component';
import { Supplier } from '../models/supplier';

/** Abre el modal de creación rápida de proveedor desde el formulario de compra (sin salir de la pantalla). */
@Injectable({
  providedIn: 'root',
})
export class SupplierQuickCreateService {
  private modal = inject(NgbModal);

  /** Devuelve el proveedor creado, o `null` si la persona cerró el modal sin guardar. */
  open(): Promise<Supplier | null> {
    const ref = this.modal.open(SupplierQuickCreateComponent, { centered: true });
    return ref.result.then(
      (supplier: Supplier) => supplier,
      () => null,
    );
  }
}
