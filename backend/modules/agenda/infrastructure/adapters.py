from datetime import date
from typing import NamedTuple
from uuid import UUID

from modules.accounting import services as accounting_services
from modules.agenda.models import AppointmentNumberCounter
from modules.customers.services import get_customer_for_sale
from modules.personnel.services import professional_exists, professional_names
from modules.service_catalog.services import get_service_for_new_use

__all__ = ['professional_exists', 'professional_names', 'get_customer_for_sale', 'get_service_for_new_use',
           'AppointmentNumbering', 'AssignedNumber', 'NumberingError']


class NumberingError(Exception):
    """No se puede numerar: sin gestión fiscal abierta para la fecha. `code` es estable para el cliente."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


class AssignedNumber(NamedTuple):
    period_id: UUID
    period_name: str
    number: int


class AppointmentNumbering:
    """Serie de citas por gestión fiscal (ADR numeración de citas): bloquea el período y su contador.

    `lock_open_period` toma la fila del período con `select_for_update`: serializa las altas de la misma gestión
    entre sí y frente a su cierre. El contador se incrementa bajo ese bloqueo y dentro de la transacción del alta, así
    un fallo posterior revierte también el número (sin huecos).
    """

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def next_number(self, day: date) -> AssignedNumber:
        try:
            period = accounting_services.lock_open_period(self.company_id, day)
        except accounting_services.DateOutsideFiscalPeriod:
            raise NumberingError(
                'fiscal_period_missing',
                f'No hay una gestión fiscal para la fecha {day.isoformat()}. Créala en Contabilidad para poder '
                'agendar citas.') from None
        except accounting_services.FiscalPeriodClosed as exc:
            raise NumberingError(
                'fiscal_period_closed',
                f'La gestión fiscal «{exc.name}» está cerrada: no se pueden agendar citas con fecha '
                f'{day.isoformat()}. Reábrela en Contabilidad.') from None
        counter, _ = AppointmentNumberCounter.objects.select_for_update().get_or_create(
            company_id=self.company_id, fiscal_period_id=period.id)
        counter.last_number += 1
        counter.save(update_fields=['last_number'])
        return AssignedNumber(period.id, period.name, counter.last_number)
