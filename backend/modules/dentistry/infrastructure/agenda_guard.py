"""Guarda que Odontología registra en Agenda: las citas con atención o de pacientes odontológicos se gestionan
por el flujo clínico (PB-ODO-007)."""
from modules.agenda.services import Veto
from shared import module_gate
from .encounter_models import EncounterModel
from .models import PatientModel

CLINICAL_FLOW = 'clinical_flow_required'
ENCOUNTER_STARTED = 'encounter_started'


def appointment_guard(company_id, appointment, action):
    if EncounterModel.objects.filter(company_id=company_id, appointment_id=appointment.id).exists():
        if action == 'attend':
            return Veto(CLINICAL_FLOW, 'Esta cita tiene una atención odontológica: finalízala desde Odontología.')
        return Veto(ENCOUNTER_STARTED,
                    'La cita tiene una atención odontológica iniciada; gestiónala desde Odontología.')
    if action == 'attend' and module_gate.is_enabled(company_id, 'dentistry') and PatientModel.objects.filter(
            company_id=company_id, customer_id=appointment.customer_id).exists():
        return Veto(CLINICAL_FLOW, 'La cita de un paciente odontológico se atiende desde Odontología.')
    return None
