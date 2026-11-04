import { tr } from '../../../core/i18n/translate';
import Swal from 'sweetalert2';
import { Profile } from '../models/profile';

export async function confirmProfileState(item: Profile): Promise<boolean> {
  const result = await Swal.fire({
    titleText: tr('PERSONNEL.PROFILE_CONFIRMATION.QUIERES_A', { p0: item.active ? 'desactivar' : 'activar', p1: item.name }),
    text: tr('PERSONNEL.PROFILE_CONFIRMATION.SE_CONSERVARAN_EL_PERFIL_SUS'), showCancelButton: true,
    confirmButtonText: tr('PERSONNEL.PROFILE_CONFIRMATION.CONFIRMAR'), cancelButtonText: tr('PERSONNEL.PROFILE_CONFIRMATION.VOLVER'),
    customClass: { confirmButton: 'btn btn-warning', cancelButton: 'btn btn-light ms-2' }, buttonsStyling: false,
  });
  return result.isConfirmed;
}
