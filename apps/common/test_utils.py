import shutil
import uuid
from pathlib import Path

from django.conf import settings
from django.test import override_settings


class TempMediaRootMixin:
    @classmethod
    def setUpClass(cls):
        test_media_root = Path(settings.BASE_DIR) / ".test_media"
        test_media_root.mkdir(exist_ok=True)
        cls._temp_media_root = test_media_root / f"test_media_{uuid.uuid4().hex}"
        cls._temp_media_root.mkdir()
        cls._media_override = override_settings(MEDIA_ROOT=str(cls._temp_media_root))
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            cls._media_override.disable()
            shutil.rmtree(cls._temp_media_root, ignore_errors=True)
