from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from modules.production.domain.recipe import Recipe, RecipeIngredient, RecipeValidationError

RESULT = uuid4()
FLOUR = uuid4()
UNIT = uuid4()


def line(product=FLOUR, quantity='2', unit=UNIT):
    return RecipeIngredient(product, unit, quantity)


def build(**changes):
    values = {'name': ' Queso ', 'result_product_id': RESULT, 'yield_quantity': '24', 'ingredients': [line()]}
    values.update(changes)
    return Recipe.create(**values)


class RecipeDomainTests(SimpleTestCase):
    def test_valid_recipe_is_normalized_and_active(self):  # AC-01, INV-01, INV-06
        recipe = build()
        self.assertEqual((recipe.name, recipe.yield_quantity, recipe.active), ('Queso', Decimal('24.0000'), True))
        self.assertEqual(recipe.ingredients[0].quantity, Decimal('2.0000'))

    def test_name_required_and_limited(self):  # INV-01
        for name in ('', '   ', None, 'x' * 151):
            with self.subTest(name=name), self.assertRaises(RecipeValidationError) as ctx:
                build(name=name)
            self.assertIn('name', ctx.exception.errors)

    def test_yield_and_quantities_must_be_positive_decimals(self):  # INV-03, INV-04, EDGE-02
        for bad in ('0', '-1', 'abc', 1.5, True, '1.00001', '', None):
            with self.subTest(yield_quantity=bad), self.assertRaises(RecipeValidationError) as ctx:
                build(yield_quantity=bad)
            self.assertIn('yield_quantity', ctx.exception.errors)
            with self.subTest(quantity=bad), self.assertRaises(RecipeValidationError) as ctx:
                build(ingredients=[line(quantity=bad)])
            self.assertIn('quantity', ctx.exception.errors['ingredients'][0])

    def test_requires_at_least_one_ingredient(self):  # INV-05
        with self.assertRaises(RecipeValidationError) as ctx:
            build(ingredients=[])
        self.assertEqual(ctx.exception.errors['ingredients'], ['Agrega al menos un ingrediente.'])

    def test_repeated_ingredient_and_result_as_ingredient(self):  # INV-05
        with self.assertRaises(RecipeValidationError) as ctx:
            build(ingredients=[line(), line(), line(product=RESULT)])
        errors = ctx.exception.errors['ingredients']
        self.assertEqual(errors[0], {})
        self.assertIn('product_id', errors[1])
        self.assertIn('product_id', errors[2])

    def test_activate_and_deactivate_are_idempotent(self):  # AC-06, INV-06
        recipe = build()
        recipe.deactivate()
        recipe.deactivate()
        self.assertFalse(recipe.active)
        recipe.activate()
        recipe.activate()
        self.assertTrue(recipe.active)

    def test_redefine_keeps_identity_and_state(self):  # AC-05
        recipe = build()
        recipe.deactivate()
        changed = recipe.redefined(name='Otro', result_product_id=RESULT, yield_quantity='12',
                                   ingredients=[line(quantity='1.5')])
        self.assertEqual((changed.id, changed.active, changed.name), (recipe.id, False, 'Otro'))
        self.assertEqual(changed.ingredients[0].quantity, Decimal('1.5000'))
