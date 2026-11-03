from uuid import uuid4
from django.test import SimpleTestCase
from modules.dentistry.domain.patient import Patient, PatientArchived, PatientInvalid


class PatientTests(SimpleTestCase):
    def test_unknown_is_empty_and_absence_requires_explicit_text(self):
        patient = Patient(uuid4())
        self.assertEqual(patient.clinical['allergies'], '')
        patient.edit({'allergies': '  Sin alergias conocidas, según paciente  '})
        self.assertEqual(patient.clinical['allergies'], 'Sin alergias conocidas, según paciente')
        patient.edit({'allergies': '   '})
        self.assertEqual(patient.clinical['allergies'], '')

    def test_invalid_edit_is_atomic(self):
        patient = Patient(uuid4())
        with self.assertRaises(PatientInvalid):
            patient.edit({'allergies': 'nuevo', 'medication': 'x' * 4001})
        self.assertEqual(patient.clinical['allergies'], '')

    def test_archive_blocks_edit_but_activation_preserves_identity(self):
        patient = Patient(uuid4())
        patient.edit({'medical_history': 'Asma'})
        original_id = patient.customer_id
        patient.archive()
        with self.assertRaises(PatientArchived):
            patient.edit({'medical_history': 'otro'})
        patient.activate()
        self.assertEqual(patient.customer_id, original_id)
        self.assertEqual(patient.clinical['medical_history'], 'Asma')
