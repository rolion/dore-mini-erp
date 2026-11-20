from datetime import timedelta
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from modules.data_import.application.ports import DuplicateSale, RunData
from modules.data_import.domain.errors import ImportRuleViolation

from .models import ImportedSaleModel, ImportRowResultModel, ImportRunModel

STALE_AFTER = timedelta(minutes=15)


def _run_data(model: ImportRunModel) -> RunData:
    return RunData(
        id=model.id, filename=model.filename, status=model.status, headers=model.headers, rows=model.rows,
        row_count=model.row_count, mapping=model.mapping, options=model.options,
        preview_signature=model.preview_signature, counts=model.counts, idempotency_key=model.idempotency_key,
        created_by_name=model.created_by_name, created_at=model.created_at, finished_at=model.finished_at)


class DjangoImportRepository:
    """Repositorio acotado a una empresa: toda consulta filtra por `company_id`."""

    def __init__(self, company_id: UUID):
        self.company_id = company_id

    def _runs(self) -> QuerySet:
        return ImportRunModel.objects.filter(company_id=self.company_id)

    def create_run(self, filename: str, sha256: str, headers: list[str], rows: list[list[str]],
                   user_id: UUID | None, user_name: str) -> RunData:
        model = ImportRunModel.objects.create(
            company_id=self.company_id, filename=filename[:255], file_sha256=sha256, headers=headers, rows=rows,
            row_count=len(rows), created_by_id=user_id, created_by_name=user_name[:150])
        return _run_data(model)

    def get_run(self, run_id: UUID) -> RunData | None:
        model = self._runs().filter(pk=run_id).first()
        return _run_data(model) if model else None

    def list_runs(self) -> QuerySet:
        return self._runs().defer('rows', 'headers')

    def save_preview(self, run_id: UUID, mapping: dict, options: dict, signature: str) -> None:
        self._runs().filter(pk=run_id).exclude(status__in=[ImportRunModel.RUNNING, ImportRunModel.COMPLETED]).update(
            mapping=mapping, options=options, preview_signature=signature, status=ImportRunModel.PREVIEWED)

    def claim(self, run_id: UUID, idempotency_key: UUID | None, now) -> None:
        """Marca la importación como en curso; una sola por empresa (INV-09). Una «en curso» sin latido reciente se
        considera caída y se marca fallida antes de reclamar."""
        with transaction.atomic():
            self._runs().filter(status=ImportRunModel.RUNNING, heartbeat_at__lt=now - STALE_AFTER).update(
                status=ImportRunModel.FAILED, finished_at=now)
            try:
                with transaction.atomic():
                    updated = self._runs().filter(pk=run_id).exclude(
                        status__in=[ImportRunModel.RUNNING, ImportRunModel.COMPLETED]).update(
                        status=ImportRunModel.RUNNING, started_at=now, heartbeat_at=now,
                        idempotency_key=idempotency_key)
            except IntegrityError:
                raise ImportRuleViolation(
                    'import_running', 'Ya hay una importación en curso en tu empresa; espera a que termine.') from None
        if not updated:
            raise ImportRuleViolation('import_not_runnable', 'La importación no se puede ejecutar en su estado actual.')
        ImportRowResultModel.objects.filter(run_id=run_id).delete()  # reintento de una corrida caída

    def heartbeat(self, run_id: UUID, now) -> None:
        self._runs().filter(pk=run_id).update(heartbeat_at=now)

    def finish(self, run_id: UUID, status: str, counts: dict, now) -> None:
        self._runs().filter(pk=run_id).update(status=status, counts=counts, finished_at=now, heartbeat_at=now)

    def existing_keys(self, keys: list[str]) -> set[str]:
        found: set[str] = set()
        for start in range(0, len(keys), 500):
            chunk = keys[start:start + 500]
            found.update(ImportedSaleModel.objects.filter(company_id=self.company_id, source_key__in=chunk)
                         .values_list('source_key', flat=True))
        return found

    def record_sale(self, key: str, order_id: UUID, run_id: UUID) -> None:
        try:
            with transaction.atomic():
                ImportedSaleModel.objects.create(company_id=self.company_id, source_key=key, order_id=order_id,
                                                 run_id=run_id)
        except IntegrityError:
            raise DuplicateSale(key) from None

    def add_result(self, run_id: UUID, row_number: int, sale_key: str, status: str, code: str, message: str,
                   order_id: UUID | None, refs: dict) -> None:
        ImportRowResultModel.objects.create(
            run_id=run_id, row_number=row_number, sale_key=sale_key[:100], status=status, code=code[:60],
            message=message, order_id=order_id, created_refs=refs)

    def list_results(self, run_id: UUID, status: str | None = None) -> QuerySet:
        queryset = ImportRowResultModel.objects.filter(run__company_id=self.company_id, run_id=run_id)
        return queryset.filter(status=status) if status else queryset
