export const WAREHOUSE_NAME_MAX_LENGTH = 150;

export interface Warehouse {
  id: string;
  name: string;
  description: string;
  active: boolean;
  isDefault: boolean;
}

export interface WarehouseInput {
  name: string;
  description: string;
  isDefault: boolean;
}

export interface WarehouseDto {
  id: string;
  name: string;
  description: string;
  active: boolean;
  is_default: boolean;
}
