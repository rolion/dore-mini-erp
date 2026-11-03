export interface ModuleLinkDto {
  key: string;
  name: string;
  enabled: boolean;
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
  };
}
