#!/usr/bin/env python3
import os
import sys


def execute(argv):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ftpvistasite.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(argv)


if __name__ == "__main__":
    execute(sys.argv)
