export interface ModuleLinkDto {
  key: string;
  name: string;
  enabled: boolean;
}

export interface ModuleCapability {
  key: string;
  label: string;
  available: boolean;
}

export interface DisableBlocker {
  code: string;
  message: string;
  resolution: string;
}

export interface ModuleDto {
  key: string;
  name: string;
  description: string;
  is_base: boolean;
  enabled: boolean;
  requires: ModuleLinkDto[];
  optional: ModuleLinkDto[];
  missing_requires: string[];
  capabilities?: ModuleCapability[];
  missing_capabilities?: string[];
  adopted_at?: string | null;
  disable_blockers?: DisableBlocker[];
}

export type ModuleLink = ModuleLinkDto;

export interface AppModule {
  key: string;
  name: string;
  description: string;
  isBase: boolean;
  enabled: boolean;
  requires: ModuleLink[];
  optional: ModuleLink[];
  /** Nombres de las dependencias obligatorias que faltan por habilitar. */
  missingRequires: string[];
  /** Capacidades de otros módulos que este exige (p. ej. valoración de Inventario). */
  capabilities: ModuleCapability[];
  /** Etiquetas de las capacidades requeridas que no están disponibles. */
  missingCapabilities: string[];
  /** Fecha de adopción (solo Costeo habilitado); `null` si no aplica. */
  adoptedAt: string | null;
  /** Datos abiertos que impiden deshabilitar el módulo, con cómo resolverlos. */
  disableBlockers: DisableBlocker[];
}

/** Módulos que siempre están habilitados; sirven de respaldo si no se puede consultar al servidor. */
export const BASE_MODULE_KEYS: readonly string[] = ['access', 'catalog'];

export class ModulesApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    /** Nombres de módulos que faltan (al habilitar) o que lo requieren (al deshabilitar). */
    readonly names: string[] = [],
  ) {
    super(message);
    this.name = 'ModulesApiError';
  }
}

export function toAppModule(dto: ModuleDto): AppModule {
  return {
    key: dto.key,
    name: dto.name,
    description: dto.description,
    isBase: dto.is_base,
    enabled: dto.enabled,
    requires: dto.requires,
    optional: dto.optional,
    missingRequires: dto.missing_requires,
    capabilities: dto.capabilities ?? [],
    missingCapabilities: dto.missing_capabilities ?? [],
    adoptedAt: dto.adopted_at ?? null,
    disableBlockers: dto.disable_blockers ?? [],
  };
}
