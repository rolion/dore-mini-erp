from uuid import UUID


class NoWarehouseActivity:
    """Todavía no existen saldos ni recepciones: ningún almacén tiene actividad que bloquee su desactivación.

    Las historias de movimientos y recepciones sustituyen este adaptador por uno que consulte sus datos.
    """

    def has_nonzero_balance(self, warehouse_id: UUID) -> bool:
        return False

    def has_pending_receipts(self, warehouse_id: UUID) -> bool:
        return False
