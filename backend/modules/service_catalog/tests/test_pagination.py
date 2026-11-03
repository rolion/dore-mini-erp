from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from modules.service_catalog.api.views import ServicePagination


class ServicePaginationTests(SimpleTestCase):
    def test_invalid_parameters_and_missing_pages_return_field_errors(self):
        for field, value in [('page', '0'), ('page', '2'), ('page', '-1'), ('page', 'abc'),
                             ('page', '9' * 5000), ('page_size', '0'), ('page_size', 'abc'),
                             ('page_size', '1.5'), ('page_size', '١')]:
            with self.subTest(field=field, value=value[:20]):
                request = Request(APIRequestFactory().get('/api/services/', {field: value}))
                with self.assertRaises(ValidationError) as caught:
                    ServicePagination().paginate_queryset([1], request)
                self.assertEqual(caught.exception.status_code, 400)
                self.assertIn(field, caught.exception.detail)

    def test_valid_pagination_and_empty_first_page(self):
        request = Request(APIRequestFactory().get('/api/services/', {'page': '2', 'page_size': '1'}))
        self.assertEqual(ServicePagination().paginate_queryset([1, 2], request), [2])
        self.assertEqual(ServicePagination().paginate_queryset([], Request(APIRequestFactory().get('/api/services/'))), [])
