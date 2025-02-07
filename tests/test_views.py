import pytest 
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.shared.addons.exceptions import CustomValidationError
from apps.shared.addons.custom_logging import logger


@pytest.mark.djang_db
class TestUserRegistrationView:

    def test_register(self, api_client) -> None:
        """
        Testing registration
        """