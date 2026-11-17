import { tr } from '../../../core/i18n/translate';
import { ProblemInfo } from './accounting';
import { PostingIssue } from './posting-config';

const KEY = 'ACCOUNTING.POSTING';

/** Texto traducido o, si la clave no existe, el respaldo en español del servidor. */
function translated(key: string, params: Record<string, unknown>, fallback: string): string {
  const text = tr(key, params);
  return text === key ? fallback : text;
}

const className = (code: string): string => translated(`${KEY}.CLASSES.${code}`, {}, code);

/** Por qué una cuenta no sirve para un rol, en el idioma activo. */
export function problemText(problem: ProblemInfo | null, fallback = ''): string {
  if (!problem) {
    return fallback;
  }
  const params: Record<string, unknown> = { ...problem.params };
  for (const key of ['actual', 'required', 'class_code']) {
    if (typeof params[key] === 'string') params[key] = className(params[key] as string);
  }
  return translated(`${KEY}.PROBLEMS.${problem.code.toUpperCase()}`, params, problem.message ?? fallback);
}

/** Nombre de un módulo en el idioma activo (el servidor lo envía en español). */
export function moduleName(module: string, fallback = module): string {
  return translated(`${KEY}.MODULES.${module}`, {}, fallback);
}

/** Nombre de un método de pago en el idioma activo (el servidor lo envía en español). */
export function methodName(code: string, fallback = code): string {
  return translated(`${KEY}.METHODS_LABEL.${code}`, {}, fallback);
}

/** Dónde se corrige: «Ventas › Configuración › Asientos automáticos», con el módulo en el idioma activo. */
function where(module: string): string {
  return tr(`${KEY}.WHERE`, { p0: moduleName(module) });
}

/** Aviso de configuración faltante, en el idioma activo; sin clave conocida, el mensaje del servidor. */
export function issueText(issue: PostingIssue): string {
  const role = translated(`${KEY}.ROLES.${issue.role}`, {}, issue.subject);
  const place = where(issue.module);
  switch (issue.code) {
    case 'role_unconfigured':
      return tr(`${KEY}.ISSUES.ROLE_UNCONFIGURED`, { subject: role, where: place });
    case 'method_unconfigured':
      return tr(`${KEY}.ISSUES.METHOD_UNCONFIGURED`, {
        method: methodName(issue.params['method_code'] ?? '', issue.params['method'] ?? ''),
        where: place,
      });
    case 'category_unconfigured':
      return issue.params['category']
        ? tr(`${KEY}.ISSUES.CATEGORY_UNCONFIGURED_NAMED`, { category: issue.params['category'], where: place })
        : tr(`${KEY}.ISSUES.CATEGORY_UNCONFIGURED`, { where: place });
    case 'category_required':
      return tr(`${KEY}.ISSUES.CATEGORY_REQUIRED`);
    case 'method_required':
      return tr(`${KEY}.ISSUES.METHOD_REQUIRED`);
    case 'account_invalid': {
      // `subject` = «<rol en español> · <método o categoría>»: el rol se reemplaza por su traducción.
      const extra = issue.subject.split(' · ').slice(1).join(' · ');
      return tr(`${KEY}.ISSUES.ACCOUNT_INVALID`, {
        problem: problemText(issue.problem, issue.message),
        subject: extra ? `${role} · ${extra}` : role,
        where: place,
      });
    }
    default:
      return issue.message;
  }
}
