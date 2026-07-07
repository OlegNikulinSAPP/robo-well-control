from rest_framework.test import APITestCase
from rest_framework import status
from core.models import Well


class TestSelectForWell(APITestCase):
    def setUp(self):
        # Создаем скважину прямо здесь
        self.well = Well.objects.create(
            id=1,
            name='Скважина 1',
            depth=1500.5,
            reservoir_pressure=15.0,
            productivity_index=2.5,
            casing_inner_diameter=168.3
        )
        self.url = '/api/pumps/select_for_well/'

    def test_no_well_id(self):
        response = self.client.get(self.url, {})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Не указан ID', str(response.data))

    def test_well_not_found(self):
        response = self.client.get(self.url, {'well_id': 999})
        self.assertEqual(response.status_code, 400)

    def test_well_id_not_number(self):
        response = self.client.get(self.url, {'well_id': 'abc'})
        self.assertEqual(response.status_code, 400)

    def test_invalid_target_flow(self):
        response = self.client.get(self.url, {
            'well_id': 1,
            'target_flow': 'не_число'
        })
        self.assertEqual(response.status_code, 400)

    def test_max_flow(self):
        response = self.client.get(self.url, {
            'well_id': 1,
            'target_flow': 500
        })
        self.assertEqual(response.status_code, 400)
