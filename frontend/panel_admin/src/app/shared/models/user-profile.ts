/** Datos de la sesión necesarios para mostrar a la persona (compatible con `User` de `@core`). */
export interface UserIdentity {
  firstName?: string;
  lastName?: string;
  username?: string;
}

const firstLetter = (text: string | undefined): string =>
  (text ?? '').trim().charAt(0).toLocaleUpperCase();

/** Nombre y apellido; si no hay, el `username`; vacío si no hay sesión. */
export function userFullName(user: UserIdentity | null | undefined): string {
  const fullName = [user?.firstName, user?.lastName]
    .map((part) => (part ?? '').trim())
    .filter(Boolean)
    .join(' ');
  return fullName || (user?.username ?? '').trim();
}

/**
 * Iniciales para el avatar: primera letra del nombre y del apellido; si no hay ninguno,
 * la del `username`; "?" si tampoco hay.
 */
export function userInitials(user: UserIdentity | null | undefined): string {
  const initials = firstLetter(user?.firstName) + firstLetter(user?.lastName);
  return initials || firstLetter(user?.username) || '?';
}
