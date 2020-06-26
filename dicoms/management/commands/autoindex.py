from django.core.management.base import BaseCommand
from django.conf import settings
from dicoms.event_logger import start_logging_and_run_indexer


class Command(BaseCommand):
    """
    This class provides the user with the ability to index dicoms automatically
    usage is as follows

    >python manage.py autoindex
    """

    # TODO add support for passing in paths to this command
    def handle(self, *args, **options):
        start_logging_and_run_indexer(path_to_watch=settings.BASE_DICOM_DIR[0],
                                      log_path=settings.LOG_PATH)


if __name__ == '__main__':
    x = Command()
    x.handle(path_to_watch=settings.BASE_DICOM_DIR, log_path=settings.LOG_PATH)
