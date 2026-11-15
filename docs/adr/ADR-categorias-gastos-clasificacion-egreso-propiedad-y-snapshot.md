# ADR-categorias-gastos-clasificacion-egreso-propiedad-y-snapshot: Dónde vive la asociación categoría→clasificación y cómo se preserva el histórico

**Estado:** Propuesto
**Task relacionado:** TASK-categorias-gastos-clasificacion-egreso
**Fecha:** 2026-11-15

## Contexto
CONT-03 pide asociar cada categoría de Gastos con una clasificación de egreso de Contabilidad y fijar una clasificación para pagos de Compras. El ADR de CONT-06 (decisión 7) fijó la dirección `expenses → accounting` y `purchases → accounting` y prohíbe `accounting → expenses/purchases`. Contabilidad no conoce las categorías, y los egresos (CONT-02) aún no existen: «no reclasificar el movimiento anterior» debe quedar garantizado desde ya para gastos y pagos.

## Decisión
1. **Cada módulo es dueño de su asociación; Contabilidad solo valida.**
   - `expenses_category.classification_id` (UUID anulable, sin FK entre módulos).
   - `purchases_settings` (nueva; `company_id` único, `payment_classification_id` UUID anulable): clasificación de pagos a proveedores. No es una categoría de Gastos ni crea gastos.
   - Contabilidad añade a su fachada `services.py` `describe_classifications(company_id, ids)` (DTO con nombre, dirección y estado) y reutiliza `validate_classification(..., 'EXPENSE')`.
2. **Instantánea al operar.** `expenses_expense.classification_id` y `purchases_payment.classification_id` (UUID anulables) guardan la clasificación vigente **al crear** el gasto o el pago. Cambiar la asociación después no toca registros anteriores; CONT-02/GAS-01/COM-01 construirán el movimiento a partir de esa instantánea. Registros previos quedan con `NULL` (sin movimiento, coherente con el corte de CONT-06).
3. **Regla al registrar** (gasto: `expense_date`; pago: `payment_date`): se consulta `accounting.coverage_status`.
   - Sin cobertura (Contabilidad deshabilitada, antes del corte o en un hueco): se guarda sin error; la instantánea se llena solo si la asociación es válida, si no queda `NULL`.
   - Con cobertura: si no hay asociación → error 400 `category_id` (gasto) o `non_field_errors` (pago) con código `classification_not_configured` y texto que indica «Contabilidad → Configuración → Egresos»; si la clasificación asociada está inactiva o dejó de ser de egreso → código `classification_invalid`. Nada se persiste.
4. **Validar al asociar:** `PUT /api/expense-categories/<id>/classification/` y `PUT /api/purchases/payment-classification/` llaman a `validate_classification(..., 'EXPENSE')`: rechazan ingreso, inactiva o de otra empresa. `classification_id: null` quita la asociación. La configuración no exige Contabilidad habilitada (se puede configurar antes de habilitar).
5. **Dependencias:** `ALLOWED_DEPENDENCIES['expenses'] = {'accounting'}`, `['purchases'] += 'accounting'`, `CONSUMERS += 'expenses'`; los imports solo en `infrastructure/adapters.py` detrás de un puerto (`ClassificationGateway`). Sin ciclos nuevos.
6. **Permisos:** los de siempre (`CompanyAdminPermission`); `required_modules` = el del módulo dueño (`expenses`/`purchases`). Un no admin recibe 403.
7. **Inactivas:** las categorías inactivas conservan su asociación y sus gastos; la lista de configuración y los selectores de registros nuevos solo ofrecen activas (regla ya existente).

## Alternativas consideradas
- **Guardar todo en `accounting`** (tabla `categoría→clasificación`): obliga a Contabilidad a conocer categorías de Gastos (viola `accounting ↛ expenses`) o a aceptar UUID sin validar.
- **Calcular la clasificación en cada lectura desde la categoría vigente:** reclasificaría el histórico al cambiar la asociación (incumple AC-3).
- **Esperar a CONT-02 para la instantánea:** dejaría AC-1/AC-3/AC-4 sin comprobación observable.
- **Reutilizar `ExpenseCategory` como clasificación** (unificar catálogos): fuera de alcance, ya descartado en CONT-01.
- **Bloquear la desactivación de una clasificación asociada:** CONT-01 fijó que desactivar solo impide usos nuevos; se prefiere avisar en la pestaña y rechazar al registrar con cobertura.

## Estrategia de rollback / mitigación
Migraciones aditivas y anulables (`expenses` 0003, `purchases` 0008), sin tocar filas existentes: revertir = `migrate expenses 0002` / `migrate purchases 0007`. El riesgo funcional es que empresas con Contabilidad habilitada y sin asociaciones no puedan registrar gastos/pagos con cobertura: se mitiga con el mensaje accionable, la pestaña «Egresos» que lista lo pendiente y la nota en el PR; el interruptor de emergencia es deshabilitar Contabilidad (sin cobertura nada se exige).

## Consecuencias
- `expenses` y `purchases` dependen formalmente de `accounting` por su fachada; Reporting no cambia.
- GAS-01/COM-01 heredan `classification_id` ya resuelto y validado, y la regla de bloqueo; solo agregan cuenta y movimiento.
- Un gasto o pago anterior a esta tarea no tiene instantánea; no se reclasifica ni se infiere.
- Hay dos catálogos de egresos (categorías y clasificaciones) unidos por la asociación hasta una tarea posterior.
