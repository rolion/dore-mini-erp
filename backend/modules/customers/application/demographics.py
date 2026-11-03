from modules.customers.domain.demographics import Demographics


class UpdateDemographics:
    def __init__(self, repository):
        self.repository = repository

    def execute(self, customer_id, changes, today, author_id, author_name):
        with self.repository.locked(customer_id):
            previous = self.repository.get(customer_id)
            values = {'birth_date': previous.birth_date, 'responsible_name': previous.responsible_name,
                      'responsible_phone': previous.responsible_phone, **changes}
            current = Demographics.validated(**values, today=today)
            if previous != current:
                self.repository.save(customer_id, current, previous, author_id, author_name)
            return current
