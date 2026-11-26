from datetime import date, timedelta
from uuid import uuid4

from django.test import SimpleTestCase

from modules.dentistry.domain import odontogram_catalog as catalog
from modules.dentistry.domain.odontogram import (
    CONFIRMED, DRAFT, Evaluation, EvaluationStateError, EvaluationValidationError,
)

TODAY = date(2026, 11, 26)


def build(findings=None, general=None, dentition='permanent', clinical_date=TODAY):
    return Evaluation.create(uuid4(), dentition, clinical_date, None,
                             [{'piece': 16, 'condition': 'healthy'}] if findings is None else findings,
                             general or [], TODAY)


def errors_of(**kwargs):
    with SimpleTestCase().assertRaises(EvaluationValidationError) as ctx:
        build(**kwargs)
    return ctx.exception.errors


class CatalogTests(SimpleTestCase):
    def test_fdi_sets_and_tooth_types(self):  # INV-01 / INV-02
        self.assertEqual(len(catalog.PERMANENT_TEETH), 32)
        self.assertEqual(len(catalog.TEMPORARY_TEETH), 20)
        self.assertIn(18, catalog.PERMANENT_TEETH)
        self.assertNotIn(19, catalog.PERMANENT_TEETH)
        self.assertIn(85, catalog.TEMPORARY_TEETH)
        self.assertNotIn(86, catalog.TEMPORARY_TEETH)
        self.assertEqual([catalog.tooth_type(p) for p in (11, 13, 14, 16, 54)],
                         ['incisor', 'canine', 'premolar', 'molar', 'molar'])

    def test_surfaces_by_piece(self):  # INV-03
        self.assertEqual(catalog.valid_surfaces(11), ('M', 'D', 'V', 'I', 'P'))
        self.assertEqual(catalog.valid_surfaces(36), ('M', 'D', 'V', 'O', 'L'))
        self.assertEqual(catalog.valid_surfaces(54), ('M', 'D', 'V', 'O', 'P'))
        self.assertEqual(catalog.valid_surfaces(83), ('M', 'D', 'V', 'I', 'L'))

    def test_compatibility_is_symmetric(self):
        for first in catalog.CONDITIONS:
            for second in catalog.CONDITIONS:
                self.assertEqual(catalog.compatible(first.code, second.code),
                                 catalog.compatible(second.code, first.code))


class ContentTests(SimpleTestCase):
    def test_mixed_accepts_temporary_and_permanent(self):  # AC-01
        evaluation = build([{'piece': 54, 'condition': 'caries', 'surfaces': ['O', 'D']},
                            {'piece': 16, 'condition': 'filling', 'surfaces': ['O']}], dentition='mixed')
        self.assertEqual([f.piece for f in evaluation.findings], [54, 16])
        self.assertEqual(evaluation.findings[0].surfaces, ('D', 'O'))

    def test_piece_must_match_dentition(self):  # AC-03
        for dentition, piece in (('permanent', 54), ('temporary', 16), ('permanent', 19), ('mixed', 56)):
            errors = errors_of(findings=[{'piece': piece, 'condition': 'healthy'}], dentition=dentition)
            self.assertIn('findings', errors, (dentition, piece))

    def test_invalid_surface_for_piece(self):  # AC-04
        cases = [(11, 'O'), (16, 'I'), (16, 'X'), (36, 'P'), (16, 'L')]
        for piece, surface in cases:
            errors = errors_of(findings=[{'piece': piece, 'condition': 'caries', 'surfaces': [surface]}])
            self.assertIn('findings', errors, (piece, surface))
        self.assertIn('findings', errors_of(findings=[{'piece': 16, 'condition': 'caries', 'surfaces': ['O', 'O']}]))

    def test_scope_rules(self):  # INV-04
        self.assertIn('findings', errors_of(findings=[{'piece': 16, 'condition': 'caries'}]))
        self.assertIn('findings', errors_of(findings=[{'piece': 16, 'condition': 'crown', 'surfaces': ['O']}]))
        build([{'piece': 16, 'condition': 'fracture'}, {'piece': 17, 'condition': 'fracture', 'surfaces': ['M']}])

    def test_other_requires_note(self):  # AC-10
        self.assertIn('findings', errors_of(findings=[{'piece': 16, 'condition': 'other', 'notes': '  '}]))
        build([{'piece': 16, 'condition': 'other', 'notes': 'Hipoplasia'}])

    def test_coexistence_and_duplicates(self):  # INV-05
        bad = [
            [{'piece': 16, 'condition': 'healthy'}, {'piece': 16, 'condition': 'crown'}],
            [{'piece': 16, 'condition': 'missing'}, {'piece': 16, 'condition': 'other', 'notes': 'x'}],
            [{'piece': 16, 'condition': 'crown'}, {'piece': 16, 'condition': 'crown'}],
            [{'piece': 16, 'condition': 'implant'}, {'piece': 16, 'condition': 'caries', 'surfaces': ['O']}],
            [{'piece': 16, 'condition': 'caries', 'surfaces': ['O']},
             {'piece': 16, 'condition': 'filling', 'surfaces': ['O', 'M']}],
        ]
        for findings in bad:
            self.assertIn('findings', errors_of(findings=findings), findings)
        build([{'piece': 16, 'condition': 'caries', 'surfaces': ['O']},
               {'piece': 16, 'condition': 'filling', 'surfaces': ['M']},
               {'piece': 16, 'condition': 'endodontics'}])

    def test_unknown_condition_and_long_texts(self):
        self.assertIn('findings', errors_of(findings=[{'piece': 16, 'condition': 'magia'}]))
        self.assertIn('findings', errors_of(findings=[{'piece': 16, 'condition': 'healthy', 'diagnosis': 'x' * 501}]))

    def test_dentition_and_date(self):  # INV-08
        self.assertIn('dentition', errors_of(dentition='otra'))
        self.assertIn('clinical_date', errors_of(clinical_date=TODAY + timedelta(days=1)))
        self.assertIn('clinical_date', errors_of(clinical_date=None))

    def test_general_findings_are_separate(self):  # AC-08 / INV-07
        evaluation = build(findings=[], general=[{'diagnosis': ' Bruxismo ', 'notes': 'Nocturno'}])
        self.assertEqual(evaluation.findings, [])
        self.assertEqual(evaluation.general_findings[0].diagnosis, 'Bruxismo')
        self.assertIn('general_findings', errors_of(findings=[], general=[{'diagnosis': '  '}]))

    def test_unevaluated_vs_healthy(self):  # AC-12 / INV-06
        evaluation = build([{'piece': 16, 'condition': 'healthy'}])
        pieces = {f.piece: f.condition for f in evaluation.findings}
        self.assertEqual(pieces.get(16), 'healthy')
        self.assertNotIn(17, pieces)


class LifecycleTests(SimpleTestCase):
    def test_confirm_requires_content_and_locks(self):  # INV-09 / AC-05
        empty = build(findings=[])
        with self.assertRaises(EvaluationValidationError):
            empty.confirm()
        evaluation = build()
        self.assertEqual(evaluation.status, DRAFT)
        evaluation.confirm()
        self.assertEqual(evaluation.status, CONFIRMED)
        for operation in (lambda: evaluation.confirm(), lambda: evaluation.ensure_discardable(),
                          lambda: evaluation.replace_content('permanent', TODAY, None, [], [], TODAY)):
            with self.assertRaises(EvaluationStateError):
                operation()
        self.assertEqual(len(evaluation.findings), 1)

    def test_replace_content_on_draft(self):
        evaluation = build()
        evaluation.replace_content('temporary', TODAY, None, [{'piece': 54, 'condition': 'healthy'}], [], TODAY)
        self.assertEqual((evaluation.dentition, evaluation.findings[0].piece), ('temporary', 54))
        with self.assertRaises(EvaluationValidationError):  # cambiar de dentición invalida piezas
            evaluation.replace_content('permanent', TODAY, None, [{'piece': 54, 'condition': 'healthy'}], [], TODAY)

    def test_amend_creates_linked_draft_and_keeps_original(self):  # INV-11 / AC-06
        original = build([{'piece': 16, 'condition': 'caries', 'surfaces': ['O']}])
        with self.assertRaises(EvaluationStateError):
            original.amend('Error de captura')  # un borrador no se enmienda
        original.confirm()
        for reason in (None, '', '   ', 'x' * 501):
            with self.assertRaises(EvaluationValidationError):
                original.amend(reason)
        amendment = original.amend('  Superficie equivocada ')
        self.assertEqual((amendment.status, amendment.amends_id, amendment.amendment_reason),
                         (DRAFT, original.id, 'Superficie equivocada'))
        self.assertEqual([f.piece for f in amendment.findings], [16])
        self.assertNotEqual(amendment.id, original.id)
        self.assertEqual(original.status, CONFIRMED)
