from modules.modularity.infrastructure.django.repositories import DjangoCompanySettingRepository

KEY = 'inventory.allow_negative_stock'


def set_negative_stock(company, allowed: bool) -> None:
    """Guarda la política de stock negativo de la empresa (como lo haría PATCH de configuración)."""
    DjangoCompanySettingRepository(company.id).save(KEY, 'true' if allowed else 'false')
