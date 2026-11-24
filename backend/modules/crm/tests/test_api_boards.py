from unittest import mock
from uuid import UUID, uuid4

from rest_framework.test import APITestCase

from modules.accounts.testing import authenticate, make_admin, make_company
from modules.crm.infrastructure.django.models import BoardModel, StageModel

URL = '/api/crm/boards/'


class FakeCards:
    """Puerto de tarjetas falso: {stage_id: cantidad}; `fail` simula un fallo a mitad de la reasignación."""

    def __init__(self, counts=None, fail=False):
        self.counts, self.fail, self.moved = dict(counts or {}), fail, []

    def count(self, stage_id):
        return self.counts.get(stage_id, 0)

    def reassign(self, from_stage_id, to_stage_id):
        self.moved.append((from_stage_id, to_stage_id))
        if self.fail:
            raise RuntimeError('boom')
        self.counts[to_stage_id] = self.counts.get(to_stage_id, 0) + self.counts.pop(from_stage_id, 0)


class BoardApiBase(APITestCase):
    def setUp(self):
        self.company = make_company('CRM A')
        self.user = make_admin(self.company, username='crm-admin')
        authenticate(self.client, self.user)

    def make_board(self, name='Ventas', *stages):
        board = self.client.post(URL, {'name': name}, format='json')
        self.assertEqual(board.status_code, 201, board.content)
        body = board.json()
        for stage in stages:
            body = self.client.post(f"{URL}{body['id']}/stages/", {'name': stage}, format='json').json()
        return body

    def ids(self, board):
        return [s['id'] for s in board['stages']]


class BoardApiTests(BoardApiBase):
    def test_create_board_is_empty_and_scoped_to_company(self):
        body = self.make_board('  Ventas  ', )
        self.assertEqual((body['name'], body['is_active'], body['stages']), ('Ventas', True, []))
        self.assertEqual(BoardModel.objects.get(pk=body['id']).company_id, self.company.id)
        sent = self.client.post(URL, {'name': 'Otro', 'company_id': str(uuid4())}, format='json').json()
        self.assertEqual(BoardModel.objects.get(pk=sent['id']).company_id, self.company.id)

    def test_duplicate_blank_and_long_names_rejected(self):
        self.make_board('Ventas')
        for name in ('ventas', '   ', 'x' * 81):
            response = self.client.post(URL, {'name': name}, format='json')
            self.assertEqual(response.status_code, 400, name)
            self.assertIn('name', response.json())

    def test_rename_archive_reactivate_and_list_filter(self):
        board = self.make_board('Ventas')
        url = f"{URL}{board['id']}/"
        self.assertEqual(self.client.patch(url, {'name': 'Comercial'}, format='json').json()['name'], 'Comercial')
        self.assertFalse(self.client.post(f'{url}archive/').json()['is_active'])
        self.assertEqual(self.client.get(URL + '?active=true').json(), [])
        self.assertEqual(len(self.client.get(URL + '?active=false').json()), 1)
        self.make_board('Comercial')  # el nombre de un archivado no bloquea
        self.assertEqual(self.client.post(f'{url}reactivate/').status_code, 400)  # ahora choca con el activo
        self.assertEqual(self.client.get(URL + '?active=maybe').status_code, 400)

    def test_stages_are_added_at_the_end_renamed_and_listed_in_order(self):
        board = self.make_board('Ventas', 'Nuevo', 'Propuesta')
        self.assertEqual([(s['name'], s['position'], s['card_count']) for s in board['stages']],
                         [('Nuevo', 1, 0), ('Propuesta', 2, 0)])
        first = board['stages'][0]['id']
        renamed = self.client.patch(f"{URL}{board['id']}/stages/{first}/", {'name': 'Lead'}, format='json').json()
        self.assertEqual(renamed['stages'][0]['name'], 'Lead')
        dup = self.client.post(f"{URL}{board['id']}/stages/", {'name': 'propuesta'}, format='json')
        self.assertEqual(dup.status_code, 400)

    def test_reorder_persists_and_rejects_bad_sets(self):
        board = self.make_board('Ventas', 'A', 'B', 'C')
        a, b, c = self.ids(board)
        url = f"{URL}{board['id']}/stages/order/"
        self.assertEqual(self.client.put(url, {'stage_ids': [c, a, b]}, format='json').status_code, 200)
        reloaded = self.client.get(f"{URL}{board['id']}/").json()
        self.assertEqual([s['name'] for s in reloaded['stages']], ['C', 'A', 'B'])
        for bad in ([a, b], [a, a, b, c], [a, b, c, str(uuid4())]):
            response = self.client.put(url, {'stage_ids': bad}, format='json')
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()['code'], 'stage_order_stale')
        self.assertEqual(self.client.put(url, {'stage_ids': ['nope']}, format='json').status_code, 400)
        self.assertEqual([s['name'] for s in self.client.get(f"{URL}{board['id']}/").json()['stages']],
                         ['C', 'A', 'B'])

    def test_archive_stage_without_cards_recompacts(self):
        board = self.make_board('Ventas', 'A', 'B', 'C')
        a, b, c = self.ids(board)
        body = self.client.post(f"{URL}{board['id']}/stages/{b}/archive/", {}, format='json').json()
        self.assertEqual([(s['name'], s['position']) for s in body['stages']], [('A', 1), ('C', 2)])
        self.assertFalse(StageModel.objects.get(pk=b).is_active)
        again = self.client.post(f"{URL}{board['id']}/stages/{b}/archive/", {}, format='json')
        self.assertEqual(again.status_code, 404)

    def test_archive_stage_with_cards_requires_target_and_moves_them(self):
        board = self.make_board('Ventas', 'A', 'B')
        a, b = self.ids(board)
        cards = FakeCards({UUID(a): 4})
        url = f"{URL}{board['id']}/stages/{a}/archive/"
        with mock.patch('modules.crm.api.views.stage_cards', return_value=cards):
            blocked = self.client.post(url, {}, format='json')
            self.assertEqual((blocked.status_code, blocked.json()['code'], blocked.json()['card_count']),
                             (409, 'stage_has_cards', 4))
            self.assertTrue(StageModel.objects.get(pk=a).is_active)
            self.assertEqual(self.client.post(url, {'target_stage_id': a}, format='json').status_code, 400)
            self.assertEqual(self.client.post(url, {'target_stage_id': str(uuid4())}, format='json').status_code, 400)
            ok = self.client.post(url, {'target_stage_id': b}, format='json')
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertEqual(cards.moved, [(UUID(a), UUID(b))])
        self.assertEqual([(s['name'], s['card_count']) for s in ok.json()['stages']], [('B', 4)])

    def test_failed_reassignment_leaves_everything_unchanged(self):
        board = self.make_board('Ventas', 'A', 'B')
        a, b = self.ids(board)
        cards = FakeCards({UUID(a): 2}, fail=True)
        self.client.raise_request_exception = False
        with mock.patch('modules.crm.api.views.stage_cards', return_value=cards):
            response = self.client.post(f"{URL}{board['id']}/stages/{a}/archive/", {'target_stage_id': b},
                                        format='json')
        self.assertEqual(response.status_code, 500)
        self.assertTrue(StageModel.objects.get(pk=a).is_active)
        self.assertEqual(StageModel.objects.get(pk=a).position, 1)

    def test_board_with_cards_cannot_be_archived(self):
        board = self.make_board('Ventas', 'A')
        cards = FakeCards({UUID(self.ids(board)[0]): 1})
        with mock.patch('modules.crm.api.views.stage_cards', return_value=cards):
            response = self.client.post(f"{URL}{board['id']}/archive/")
        self.assertEqual((response.status_code, response.json()['code']), (409, 'board_has_cards'))
        self.assertTrue(BoardModel.objects.get(pk=board['id']).is_active)


class BoardAccessTests(BoardApiBase):
    def test_other_company_ids_are_404_everywhere(self):
        other_company = make_company('CRM B')
        other = BoardModel.objects.create(company_id=other_company.id, name='Ajeno')
        stage = StageModel.objects.create(board=other, name='X', position=1)
        mine = self.make_board('Ventas', 'A', 'B')
        my_stage = self.ids(mine)[0]
        base = f'{URL}{other.id}/'
        calls = [
            self.client.get(base), self.client.patch(base, {'name': 'x'}, format='json'),
            self.client.post(base + 'archive/'), self.client.post(base + 'reactivate/'),
            self.client.post(base + 'stages/', {'name': 'x'}, format='json'),
            self.client.patch(f'{base}stages/{stage.id}/', {'name': 'x'}, format='json'),
            self.client.put(base + 'stages/order/', {'stage_ids': [str(stage.id)]}, format='json'),
            self.client.post(f'{base}stages/{stage.id}/archive/', {}, format='json'),
            # etapa ajena bajo mi tablero, y destino ajeno
            self.client.patch(f"{URL}{mine['id']}/stages/{stage.id}/", {'name': 'x'}, format='json'),
            self.client.post(f"{URL}{mine['id']}/stages/{stage.id}/archive/", {}, format='json'),
        ]
        self.assertEqual([c.status_code for c in calls], [404] * len(calls))
        target = self.client.post(f"{URL}{mine['id']}/stages/{my_stage}/archive/",
                                  {'target_stage_id': str(stage.id)}, format='json')
        self.assertEqual(target.status_code, 400)  # un destino ajeno nunca resuelve, aunque la etapa no tenga tarjetas
        self.assertEqual(self.client.get(URL).json()[0]['name'], 'Ventas')
        self.assertEqual(len(self.client.get(URL).json()), 1)
        self.assertTrue(StageModel.objects.get(pk=stage.id).is_active)

    def test_foreign_target_with_cards_is_400_and_moves_nothing(self):
        other = BoardModel.objects.create(company_id=make_company('CRM C').id, name='Ajeno')
        foreign = StageModel.objects.create(board=other, name='X', position=1)
        mine = self.make_board('Ventas', 'A')
        a = self.ids(mine)[0]
        cards = FakeCards({UUID(a): 1})
        with mock.patch('modules.crm.api.views.stage_cards', return_value=cards):
            response = self.client.post(f"{URL}{mine['id']}/stages/{a}/archive/",
                                        {'target_stage_id': str(foreign.id)}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(cards.moved, [])

    def test_unauthenticated_and_company_less_users_are_rejected(self):
        self.client.credentials()
        self.assertEqual(self.client.get(URL).status_code, 401)
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(username='sin-empresa', password='x-Pass-123')
        authenticate(self.client, user)
        self.assertEqual(self.client.get(URL).status_code, 403)
        self.assertEqual(self.client.post(URL, {'name': 'X'}, format='json').status_code, 403)

    def test_requires_customers_module(self):
        from modules.modularity.infrastructure.django.models import CompanyModuleModel
        self.client.get(URL)  # siembra los módulos por defecto
        CompanyModuleModel.objects.filter(company_id=self.company.id, module_key='customers').delete()
        response = self.client.get(URL)
        self.assertEqual((response.status_code, response.json()['code']), (403, 'module_disabled'))
