from unittest.mock import Mock, patch

from django.test import TestCase
from elasticmodels.runner import ESTestCase

id_counter = 0


def id_generator(*args, **kwargs):
    global id_counter
    id_counter += 1
    return str(id_counter)


patches = [
    patch("alma.requests.models.create_booking", lambda *args, **kwargs: {"request_id": id_generator()}),
    patch("alma.requests.models.delete_booking", Mock()),
    patch("alma.loans.models.create_loan", Mock(side_effect=lambda *args, **kwargs: {"loan_id": id_generator()})),
    patch("alma.loans.models.return_loan", Mock()),
]


class BaseTest(TestCase):
    """
    Mocks up stuff in the Alma API so we don't accidentally create requests and
    loans for people
    """
    def setUp(self):
        for p in patches:
            p.start()
        super().setUp()

    def tearDown(self):
        super().tearDown()
        for p in patches:
            p.stop()


class AlmaTest(BaseTest):
    pass


class AlmaESTest(BaseTest, ESTestCase):
    pass
