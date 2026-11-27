"""Casos de uso de evaluaciones odontológicas (PB-ODO-002)."""
from django.db import transaction
from django.utils import timezone

from modules.dentistry.domain.patient import PatientArchived, PatientNotFound
from modules.dentistry.domain.proforma import DentalProformaValidationError
from modules.dentistry.domain.odontogram import (
    CONFIRMED, DRAFT, Evaluation, EvaluationStateError, EvaluationValidationError,
)


class EvaluationCommands:
    def __init__(self, repository, patients, gate, professionals):
        self.repository, self.patients, self.gate, self.professionals = repository, patients, gate, professionals

    @staticmethod
    def _today():
        return timezone.localdate()

    def _check_professional(self, professional_id):
        if professional_id is not None and not self.professionals.exists(professional_id):
            raise EvaluationValidationError({'professional_id': ['El profesional no existe en esta empresa.']})

    def _lock_patient(self, customer_id):
        """Serializa altas y enmiendas del mismo paciente y exige un perfil y un cliente activos."""
        self.patients.get(customer_id, locked=True)
        try:
            self.gate.require_active(customer_id)
        except PatientArchived as exc:
            raise EvaluationStateError('Reactiva el perfil odontológico antes de registrar evaluaciones.') from exc
        except DentalProformaValidationError as exc:
            raise EvaluationStateError('El cliente está inactivo; actívalo antes de registrar evaluaciones.') from exc

    def _locked_row(self, evaluation_id):
        """Orden único de bloqueos (paciente y luego evaluación) para que operaciones simultáneas se serialicen."""
        row = self.repository.get(evaluation_id)
        self.patients.get(row.customer_id, locked=True)
        return self.repository.get(evaluation_id, locked=True)

    def _ensure_no_draft(self, customer_id):
        draft = self.repository.draft_of(customer_id)
        if draft is not None:
            raise EvaluationStateError(
                f'El paciente ya tiene la evaluación #{draft.sequence} en borrador; confírmala o descártala antes.')

    @transaction.atomic
    def create(self, customer_id, data, author_id, author_name):
        self._lock_patient(customer_id)
        self._ensure_no_draft(customer_id)
        self._check_professional(data.get('professional_id'))
        evaluation = Evaluation.create(
            customer_id, data.get('dentition'), data.get('clinical_date'), data.get('professional_id'),
            data.get('findings'), data.get('general_findings'), self._today())
        return self.repository.create(evaluation, self.repository.next_sequence(customer_id), author_id, author_name)

    @transaction.atomic
    def update(self, evaluation_id, data):
        row = self._locked_row(evaluation_id)
        evaluation = self.repository.entity(row)
        evaluation.ensure_draft()  # una confirmada responde 409 antes de cualquier otra comprobación
        self._lock_patient(row.customer_id)
        self._check_professional(data.get('professional_id'))
        evaluation.replace_content(
            data.get('dentition'), data.get('clinical_date'), data.get('professional_id'),
            data.get('findings'), data.get('general_findings'), self._today())
        self.repository.save_content(row, evaluation)
        return row

    @transaction.atomic
    def discard(self, evaluation_id):
        row = self._locked_row(evaluation_id)
        self.repository.entity(row).ensure_discardable()
        self._lock_patient(row.customer_id)
        self.repository.delete(row)

    @transaction.atomic
    def confirm(self, evaluation_id, author_id, author_name):
        row = self._locked_row(evaluation_id)
        evaluation = self.repository.entity(row)
        evaluation.confirm()  # 409 si ya estaba confirmada; 400 si no tiene hallazgos
        self._lock_patient(row.customer_id)
        self.repository.save_confirmed(row, author_id, author_name)
        return row

    @transaction.atomic
    def amend(self, evaluation_id, reason, author_id, author_name):
        source = self._locked_row(evaluation_id)
        self._lock_patient(source.customer_id)
        evaluation = self.repository.entity(source)
        amendment = evaluation.amend(reason)
        self._ensure_no_draft(source.customer_id)
        if self.repository.rows().filter(amends_id=source.id, status=CONFIRMED).exists():
            raise EvaluationStateError('Esta evaluación ya fue corregida por una evaluación confirmada posterior.')
        return self.repository.create(
            amendment, self.repository.next_sequence(source.customer_id), author_id, author_name)


class EvaluationQueries:
    def __init__(self, repository, patients, professionals):
        self.repository, self.patients, self.professionals = repository, patients, professionals

    def list(self, customer_id):
        self.patients.get(customer_id)  # PatientNotFound → 404
        rows = list(self.repository.for_customer(customer_id))
        replaced = self._replaced_by(rows)
        return rows, replaced

    def _replaced_by(self, rows):
        confirmed = self.repository.rows().filter(
            amends_id__in=[row.id for row in rows], status=CONFIRMED).values_list('amends_id', 'id', 'sequence')
        return {source: (new_id, sequence) for source, new_id, sequence in confirmed}

    def summaries(self, rows, replaced):
        names = self.professionals.names({row.professional_id for row in rows if row.professional_id})
        return [self._summary(row, replaced, names) for row in rows]

    @staticmethod
    def _summary(row, replaced, names):
        new = replaced.get(row.id)
        return {
            'id': row.id, 'customer_id': row.customer_id, 'sequence': row.sequence, 'status': row.status,
            'dentition': row.dentition, 'clinical_date': row.clinical_date,
            'professional': ({'id': row.professional_id, 'name': names.get(row.professional_id, '')}
                             if row.professional_id else None),
            'author': {'id': row.created_by, 'name': row.created_by_name}, 'created_at': row.created_at,
            'confirmed_at': row.confirmed_at,
            'confirmed_by': ({'id': row.confirmed_by, 'name': row.confirmed_by_name} if row.confirmed_at else None),
            'amends_id': row.amends_id, 'amends_sequence': row.amends.sequence if row.amends_id else None,
            'amendment_reason': row.amendment_reason,
            'replaced_by_id': new[0] if new else None, 'replaced_by_sequence': new[1] if new else None,
            'catalog_version': row.catalog_version,
        }

    def detail(self, row):
        row = self.repository.rows().select_related('amends').prefetch_related(
            'findings', 'general_findings').get(pk=row.pk)
        replaced = self._replaced_by([row])
        data = self.summaries([row], replaced)[0]
        data['findings'] = [{'id': f.id, 'piece': f.piece, 'surfaces': list(f.surfaces), 'condition': f.condition,
                             'diagnosis': f.diagnosis, 'notes': f.notes} for f in row.findings.all()]
        data['general_findings'] = [{'id': g.id, 'diagnosis': g.diagnosis, 'notes': g.notes}
                                    for g in row.general_findings.all()]
        data['allowed_actions'] = self._allowed_actions(row, replaced)
        return data

    def _allowed_actions(self, row, replaced):
        try:
            patient = self.patients.get(row.customer_id)
        except PatientNotFound:  # sin perfil no hay acciones
            return []
        if not patient.active:
            return []
        if row.status == DRAFT:
            return ['edit', 'confirm', 'discard']
        if row.id not in replaced and self.repository.draft_of(row.customer_id) is None:
            return ['amend']
        return []
