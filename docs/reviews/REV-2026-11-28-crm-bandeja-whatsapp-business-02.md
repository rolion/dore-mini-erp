# REV-2026-11-28-crm-bandeja-whatsapp-business-02: AC-12: no hay prueba de migración con datos previos ni reversa

**Status:** Closed (verificado en 2º Quality Gate)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-28-crm-bandeja-whatsapp-business.md (v1)
**Spec reference:** PLAN Test Specification → Integration tests («Migración 0002 sobre filas existentes»); AC-12; mapping AC-12
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan exige una prueba de migración con datos previos. test_existing_conversations_survive_the_migration_without_links (crm/tests/test_api_inbox.py:338) solo crea una conversación con el esquema ya migrado y comprueba que los campos nuevos son NULL; no ejecuta 0001→0002 ni 0002→0001.

## Expected behavior
Una prueba (MigrationExecutor o equivalente) que cree filas en 0001, migre a 0002 y verifique que se conservan sin vínculos, y que la reversa a 0001 funciona.

## Actual behavior
AC-12 queda verificado solo de forma nominal en la suite. (El revisor lo comprobó a mano: ver Evidence; la migración en sí es correcta, el hueco es de cobertura.)

## Evidence
Verificación manual del revisor (script temporal fuera del repo, base de pruebas descartable): migrate a messaging 0001, insertar conexión + conversación, migrate a 0002 → `FORWARD OK 59100000 None None None None`; migrate de vuelta a 0001 → `REVERSE OK rows 1`. `makemigrations --check --dry-run` → "No changes detected".


## Resolution
Nueva `messaging/tests/test_migrations.py` (0001→0002→0001 con datos).
