from django.core.management.base import BaseCommand
import subprocess


class Command(BaseCommand):
    """
    This class provides the user with the ability to index dicoms automatically
    usage is as follows

    This is really goofy, but it works. I spawn the autoindex manage.py process
    in a separate thread so that it behaves silently.
    TODO Currently testing out to see
    TODO if it actually tracks changes and makes some indexs. May need to properly test
    TODO tomorrow by changing the time window down to a smaller value and manually
    TODO transfer some files 09/05/2019


    >python manage.py autoindex
    """

    def handle(self, *args, **options):
        subprocess.Popen(['python', 'manage.py', 'autoindex'])
