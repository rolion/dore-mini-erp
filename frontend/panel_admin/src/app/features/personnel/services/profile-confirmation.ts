import Swal from 'sweetalert2';
import { Profile } from '../models/profile';

export async function confirmProfileState(item: Profile): Promise<boolean> {
  const result = await Swal.fire({
    titleText: `¿Quieres ${item.active ? 'desactivar' : 'activar'} a «${item.name}»?`,
    text: 'Se conservarán el perfil, sus vínculos y su autoría histórica.', showCancelButton: true,
    confirmButtonText: 'Confirmar', cancelButtonText: 'Volver',
    customClass: { confirmButton: 'btn btn-warning', cancelButton: 'btn btn-light ms-2' }, buttonsStyling: false,
  });
  return result.isConfirmed;
}
