import tempfile
import shutil
from django.conf import settings
from elasticmodels import SearchRunner


class TestRunner(SearchRunner):
    """
    Set whatever test settings need to be in place when you run tests
    """
    def run_tests(self, *args, **kwargs):
        settings.TEST = True
        media_root = tempfile.mkdtemp()
        settings.MEDIA_ROOT = media_root
        settings.CELERY_ALWAYS_EAGER = True
        settings.PASSWORD_HASHERS = (
            'django.contrib.auth.hashers.MD5PasswordHasher',
        )

        code = super().run_tests(*args, **kwargs)
        shutil.rmtree(media_root)
        return code
