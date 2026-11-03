from django.db import IntegrityError, transaction

from modules.dentistry.domain.patient import DuplicatePatient, Patient, PatientNotFound


class PatientCommands:
    def __init__(self, repository, customers):
        self.repository, self.customers = repository, customers

    def create(self, customer_id, changes, author_id, author_name):
        if customer_id not in self.customers.get_many([customer_id]):
            raise PatientNotFound('Cliente no encontrado.')
        patient = Patient(customer_id)
        patient.edit(changes)
        try:
            with transaction.atomic():
                row = self.repository.create(patient, author_id)
                self.repository.audit(row, author_id, author_name, 'create', {}, patient.snapshot())
                return row
        except IntegrityError as exc:
            if self.repository.rows().filter(customer_id=customer_id).exists():
                raise DuplicatePatient('El cliente ya tiene un perfil odontológico.') from exc
            raise

    @transaction.atomic
    def change(self, customer_id, changes, action, author_id, author_name):
        row = self.repository.get(customer_id, locked=True)
        patient = self.repository.entity(row)
        before = patient.snapshot()
        if action == 'archive':
            patient.archive()
        elif action == 'activate':
            patient.activate()
        else:
            patient.edit(changes)
        if before != patient.snapshot():
            self.repository.save(row, patient, author_id)
            self.repository.audit(row, author_id, author_name, action, before, patient.snapshot())
        return row


class PatientQueries:
    def __init__(self, repository, customers):
        self.repository, self.customers = repository, customers

    def list(self, search, active):
        rows = self.repository.rows()
        if search:
            rows = rows.filter(customer_id__in=self.customers.search_ids(search))
        if active is not None:
            rows = rows.filter(active=active)
        return rows

    def summaries(self, rows):
        customers = self.customers.get_many([row.customer_id for row in rows])
        return [self.summary(row, customers.get(row.customer_id)) for row in rows]

    @staticmethod
    def summary(row, customer):
        return {'id': row.customer_id, 'customer': {'id': row.customer_id,
                'name': customer.name if customer else 'Cliente no disponible',
                'phone': customer.phone if customer else '', 'email': customer.email if customer else '',
                'active': customer.active if customer else False,
                'birth_date': customer.birth_date if customer else None,
                'responsible_name': customer.responsible_name if customer else '',
                'responsible_phone': customer.responsible_phone if customer else ''},
                'active': row.active, 'created_at': row.created_at, 'updated_at': row.updated_at,
                'created_by': row.created_by, 'updated_by': row.updated_by}

    def detail(self, row):
        return {**self.summaries([row])[0], **self.repository.entity(row).clinical}
