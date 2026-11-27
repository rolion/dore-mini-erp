"""Casos de uso de la atención odontológica (PB-ODO-007).

Orden de bloqueo fijo: cita (y agenda del profesional) → atención. Cada comando es una única transacción: si falla
la sincronización con la cita, no cambia la atención y viceversa.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.dentistry.domain.encounter import (
    Encounter, EncounterNotFound, EncounterStateError, EncounterValidationError, FINISHED, IN_PROGRESS, PENDING,
)
from modules.dentistry.domain.odontogram import DRAFT, EvaluationStateError
from modules.dentistry.domain.patient import PatientArchived, PatientNotFound
from modules.dentistry.domain.proforma import DentalProformaValidationError

MAX_RANGE_DAYS = 31
ZONE = ZoneInfo('America/La_Paz')  # misma zona que Agenda: el cliente muestra la hora tal como llega


def local(value: datetime | None) -> str | None:
    return value.astimezone(ZONE).isoformat() if value else None


def clinical_date(encounter_row) -> date:
    """Día clínico de la atención en la zona de Agenda, no en la del servidor (REV-08)."""
    return encounter_row.started_at.astimezone(ZONE).date()


class EncounterCommands:
    def __init__(self, repository, evaluations, evaluation_commands, patients, gate, appointments):
        self.repository, self.evaluations, self.evaluation_commands = repository, evaluations, evaluation_commands
        self.patients, self.gate, self.appointments = patients, gate, appointments

    def _locked_appointment(self, appointment_id):
        snapshot = self.appointments.lock(appointment_id)
        if snapshot is None:
            raise EncounterNotFound('Cita no encontrada.')
        return snapshot

    def _locked_encounter(self, appointment_id):
        row = self.repository.for_appointment(appointment_id, locked=True)
        if row is None:
            raise EncounterNotFound('La atención de esta cita no se ha iniciado.')
        return row

    def _require_patient(self, customer_id):
        try:
            self.gate.require_active(customer_id)
        except PatientNotFound as exc:
            raise EncounterStateError('El paciente de la cita no tiene perfil odontológico.', 'not_dental') from exc
        except PatientArchived as exc:
            raise EncounterStateError('Reactiva el perfil odontológico del paciente antes de atenderlo.',
                                      'patient_archived') from exc
        except DentalProformaValidationError as exc:
            raise EncounterStateError('El cliente está inactivo; actívalo antes de atenderlo.',
                                      'customer_inactive') from exc

    @transaction.atomic
    def start(self, appointment_id, author_id, author_name):
        """Crea la atención de la cita o devuelve la existente en progreso. Devuelve (fila, creada)."""
        snapshot = self._locked_appointment(appointment_id)
        existing = self.repository.for_appointment(appointment_id, locked=True)
        if existing is not None:
            if existing.status == IN_PROGRESS:
                return existing, False
            raise EncounterStateError('La atención de esta cita ya terminó; para otra visita crea una nueva cita.',
                                      f'encounter_{existing.status}')
        if 'attend' not in snapshot.allowed_actions:
            if snapshot.status in ('scheduled', 'confirmed'):
                raise EncounterStateError('La cita aún no llegó a su hora de inicio.', 'too_early')
            raise EncounterStateError('La cita no admite iniciar la atención en su estado actual.', 'not_eligible')
        self._require_patient(snapshot.customer_id)
        encounter = Encounter(appointment_id, snapshot.customer_id, snapshot.professional_id,
                              started_at=timezone.now())
        try:
            with transaction.atomic():
                return self.repository.create(encounter, author_id, author_name), True
        except IntegrityError:  # otra petición la creó entre medias
            row = self.repository.for_appointment(appointment_id, locked=True)
            if row is None:
                raise
            return row, False

    @transaction.atomic
    def finish(self, appointment_id, author_id, author_name):
        self._locked_appointment(appointment_id)
        row = self._locked_encounter(appointment_id)
        encounter = self.repository.entity(row)
        if encounter.status == FINISHED:
            return row  # idempotente
        encounter.ensure_in_progress()
        if self.evaluations.rows().filter(encounter=row, status=DRAFT).exists():
            raise EncounterStateError('Confirma o descarta el odontograma en borrador antes de finalizar.',
                                      'draft_pending')
        self.appointments.attend(author_id, author_name, appointment_id)
        encounter.finish(timezone.now())
        self.repository.save(row, encounter, author_id, author_name)
        return row

    @transaction.atomic
    def cancel(self, appointment_id, reason, author_id, author_name):
        self._locked_appointment(appointment_id)
        row = self._locked_encounter(appointment_id)
        encounter = self.repository.entity(row)
        encounter.cancel(reason, timezone.now())
        self.appointments.cancel(author_id, author_name, appointment_id, encounter.cancellation_reason)
        self.repository.save(row, encounter, author_id, author_name)
        return row

    @transaction.atomic
    def set_observations(self, encounter_id, text):
        row = self.repository.get(encounter_id, locked=True)
        encounter = self.repository.entity(row)
        encounter.set_observations(text)
        self.repository.save(row, encounter)
        return row

    @transaction.atomic
    def create_odontogram(self, encounter_id, data, author_id, author_name):
        row = self.repository.get(encounter_id, locked=True)
        self.repository.entity(row).ensure_in_progress()
        self._require_patient(row.customer_id)  # perfil archivado o cliente inactivo: código propio, no «borrador»
        if self.evaluations.rows().filter(encounter=row, amends__isnull=True).exists():
            raise EncounterStateError('La atención ya tiene un odontograma; continúa con el existente.',
                                      'odontogram_exists')
        payload = {'dentition': data.get('dentition') or 'permanent', 'clinical_date': clinical_date(row),
                   'professional_id': row.professional_id, 'findings': data.get('findings') or [],
                   'general_findings': data.get('general_findings') or []}
        try:
            with transaction.atomic():
                return self.evaluation_commands.create(row.customer_id, payload, author_id, author_name,
                                                       encounter_id=row.id)
        except IntegrityError as exc:
            raise EncounterStateError('La atención ya tiene un odontograma; continúa con el existente.',
                                      'odontogram_exists') from exc
        except EvaluationStateError as exc:
            raise EncounterStateError(str(exc), 'draft_exists') from exc


class EncounterQueries:
    def __init__(self, repository, evaluations, patients, customers, appointments, professionals):
        self.repository, self.evaluations, self.patients = repository, evaluations, patients
        self.customers, self.appointments, self.professionals = customers, appointments, professionals

    # --- listado clínico -------------------------------------------------------------------------------------
    def listing(self, *, first_day, last_day, professional_id, customer_id, search, status, encounter_status,
                offset, limit):
        """El costo depende del rango pedido (≤31 días): se parte de las citas del rango y se filtra en memoria."""
        if (last_day - first_day).days >= MAX_RANGE_DAYS:
            raise EncounterValidationError({'to': [f'Indica un rango de hasta {MAX_RANGE_DAYS} días.']})
        candidates = self.appointments.in_range(
            first_day=first_day, last_day=last_day, professional_id=professional_id, status=status)
        if customer_id:
            candidates = [item for item in candidates if item.customer_id == customer_id]
        dental = set(self.patients.rows().filter(
            customer_id__in={item.customer_id for item in candidates}).values_list('customer_id', flat=True))
        if search:
            dental &= set(self.customers.search_ids(search))
        candidates = [item for item in candidates if item.customer_id in dental]
        by_appointment = {row.appointment_id: row for row in self.repository.rows().filter(
            appointment_id__in=[item.id for item in candidates])}

        def state(item):
            row = by_appointment.get(item.id)
            return row.status if row else PENDING
        if encounter_status:
            candidates = [item for item in candidates if state(item) == encounter_status]
        page = candidates[offset:offset + limit]
        names = self.professionals.names({item.professional_id for item in page})
        return len(candidates), [self._list_item(item, by_appointment.get(item.id), names) for item in page]

    @staticmethod
    def _list_item(snapshot, encounter, names):
        return {
            'appointment_id': snapshot.id, 'customer_id': snapshot.customer_id,
            'customer_name': snapshot.customer_name, 'professional_id': snapshot.professional_id,
            'professional_name': names.get(snapshot.professional_id, ''), 'service_name': snapshot.service_name,
            'starts': local(snapshot.starts), 'ends': local(snapshot.ends), 'status': snapshot.status,
            'encounter_id': encounter.id if encounter else None,
            'encounter_status': encounter.status if encounter else PENDING,
        }

    # --- detalle ---------------------------------------------------------------------------------------------
    def detail(self, appointment_id):
        snapshot = self.appointments.get(appointment_id)
        if snapshot is None:
            raise EncounterNotFound('Cita no encontrada.')
        row = self.repository.for_appointment(appointment_id)
        patient_row = self.patients.rows().filter(customer_id=snapshot.customer_id).first()
        names = self.professionals.names({snapshot.professional_id})
        data = {
            'appointment': {
                'id': snapshot.id, 'customer_id': snapshot.customer_id, 'customer_name': snapshot.customer_name,
                'professional_id': snapshot.professional_id,
                'professional_name': names.get(snapshot.professional_id, ''), 'service_name': snapshot.service_name,
                'starts': local(snapshot.starts), 'ends': local(snapshot.ends), 'status': snapshot.status,
                'notes': snapshot.notes},
            'is_dental': patient_row is not None,
            'patient': self._patient(snapshot.customer_id, patient_row),
            'encounter': self._encounter(row),
            'odontogram': self._odontogram(row),
            'prescriptions_enabled': False,  # no existe recetario; contrato futuro en el ADR
        }
        data['allowed_actions'] = self._allowed_actions(snapshot, row, patient_row)
        return data

    @staticmethod
    def _allowed_actions(snapshot, row, patient_row):
        if row is not None:
            return ['finish', 'cancel'] if row.status == IN_PROGRESS else []
        if patient_row is not None and patient_row.active and 'attend' in snapshot.allowed_actions:
            return ['start']
        return []

    def _patient(self, customer_id, patient_row):
        customer = self.customers.get_many([customer_id]).get(customer_id)
        data = {'id': customer_id, 'name': customer.name if customer else '',
                'phone': customer.phone if customer else '', 'email': customer.email if customer else '',
                'birth_date': customer.birth_date if customer else None,
                'active': bool(patient_row and patient_row.active)}
        if patient_row is not None:
            data.update({key: getattr(patient_row, key) for key in
                         ('medical_history', 'dental_history', 'allergies', 'medication')})
        return data

    @staticmethod
    def _encounter(row):
        if row is None:
            return None
        return {
            'id': row.id, 'status': row.status, 'started_at': local(row.started_at),
            'started_by': {'id': row.started_by, 'name': row.started_by_name},
            'finished_at': local(row.finished_at),
            'finished_by': {'id': row.finished_by, 'name': row.finished_by_name} if row.finished_at else None,
            'cancelled_at': local(row.cancelled_at),
            'cancelled_by': {'id': row.cancelled_by, 'name': row.cancelled_by_name} if row.cancelled_at else None,
            'cancellation_reason': row.cancellation_reason, 'observations': row.observations,
        }

    def _odontogram(self, row):
        """Odontograma lógico de la atención: la raíz y la versión más reciente (enmiendas incluidas)."""
        if row is None:
            return {'can_create': False, 'root': None, 'current': None}
        rows = list(self.evaluations.rows().filter(encounter=row).order_by('sequence'))
        root = next((e for e in rows if e.amends_id is None), None)
        current = rows[-1] if rows else None

        def brief(e):
            return {'id': e.id, 'sequence': e.sequence, 'status': e.status} if e else None
        return {'can_create': row.status == IN_PROGRESS and root is None, 'root': brief(root),
                'current': brief(current), 'versions': len(rows)}

    # --- historial -------------------------------------------------------------------------------------------
    def history(self, customer_id):
        self.patients.get(customer_id)  # PatientNotFound → 404
        return self.repository.for_customer(customer_id)

    def history_items(self, rows):
        appointments = self.appointments.get_many([row.appointment_id for row in rows])
        names = self.professionals.names({row.professional_id for row in rows})
        with_odontogram = set(self.evaluations.rows().filter(
            encounter__in=[row.id for row in rows], amends__isnull=True).values_list('encounter_id', flat=True))
        items = []
        for row in rows:
            appointment = appointments.get(row.appointment_id)
            items.append({
                'id': row.id, 'appointment_id': row.appointment_id, 'status': row.status,
                'started_at': local(row.started_at), 'finished_at': local(row.finished_at),
                'professional_id': row.professional_id, 'professional_name': names.get(row.professional_id, ''),
                'service_name': appointment.service_name if appointment else '',
                'has_odontogram': row.id in with_odontogram,
            })
        return items
