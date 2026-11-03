from unittest import TestCase
from uuid import uuid4

from modules.personnel.domain.profiles import Professional, ProfileValidationError, Specialty


class ProfileDomainTests(TestCase):
    def test_minimal_professional(self):
        profile = Professional()
        profile.edit({'name': ' Ana '})
        self.assertEqual(profile.name, 'Ana')
        self.assertIsNone(profile.user_id)
        self.assertEqual(profile.specialty_ids, [])

    def test_invalid_name_and_lengths(self):
        for values in ({'name': ''}, {'name': '  '}, {'name': 'x' * 151}, {'name': 42},
                       {'name': 'Ana', 'identification': 'x' * 51}, {'name': 'Ana', 'phone': 'x' * 31},
                       {'name': 'Ana', 'registration_number': 'x' * 101}, {'name': 'Ana', 'email': 'x' * 255}):
            with self.subTest(values=values), self.assertRaises(ProfileValidationError):
                Professional().edit(values)

    def test_invalid_edit_does_not_mutate(self):
        profile = Professional(name='Ana')
        with self.assertRaises(ProfileValidationError):
            profile.edit({'name': 'Otra', 'email': 'invalid'})
        self.assertEqual(profile.name, 'Ana')

    def test_optional_contact_and_deduplication(self):
        specialty = uuid4()
        profile = Professional(name='Ana')
        profile.edit({'phone': ' 123 ', 'email': ' a@b.com ', 'specialty_ids': [specialty, specialty]})
        self.assertEqual(profile.phone, '123')
        self.assertEqual(profile.email, 'a@b.com')
        self.assertEqual(profile.specialty_ids, [specialty])
        profile.edit({'user_id': 7})
        profile.deactivate()
        self.assertEqual(profile.user_id, 7)
        profile.activate()
        profile.edit({'user_id': None})
        self.assertTrue(profile.active)
        self.assertIsNone(profile.user_id)

    def test_specialty_lifecycle(self):
        item = Specialty()
        item.edit({'name': ' Ortodoncia '})
        item.deactivate()
        self.assertEqual(item.name, 'Ortodoncia')
        self.assertFalse(item.active)
        item.activate()
        self.assertTrue(item.active)
