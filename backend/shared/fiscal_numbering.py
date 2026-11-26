"""Numeración correlativa por empresa y período fiscal, compartida por Ventas, Compras e Inventario (lotes).

Cada módulo conserva su propio modelo de contador (tabla y restricciones propias) y su excepción de dominio: aquí solo
vive lo común (bloquear el período abierto e incrementar el contador bajo ese bloqueo).
"""
from datetime import date
from uuid import UUID

from modules.accounting import services as accounting_services


def allocate_period_number(company_id: UUID, on_date: date, counter_model) -> tuple[accounting_services.PeriodRef, int]:
    """Bloquea el período fiscal abierto de `on_date` y devuelve `(período, siguiente número)`.

    Debe ejecutarse dentro de la transacción de quien numera: el número se revierte con ella (sin huecos).
    `lock_open_period` toma la fila del período con `select_for_update`, lo que serializa las asignaciones del mismo
    período entre sí y frente a su cierre. Deja pasar `DateOutsideFiscalPeriod` y `FiscalPeriodClosed` para que cada
    módulo las traduzca a su excepción. `counter_model` tiene `company_id`, `fiscal_period_id` y `last_number`.
    """
    period = accounting_services.lock_open_period(company_id, on_date)
    counter, _ = counter_model.objects.select_for_update().get_or_create(
        company_id=company_id, fiscal_period_id=period.id)
    counter.last_number += 1
    counter.save(update_fields=['last_number'])
    return period, counter.last_number
