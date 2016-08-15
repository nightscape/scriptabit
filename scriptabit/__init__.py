# -*- coding: utf-8 -*-
""" scriptabit

    Python scripting for Habitica via the API
"""

from .authentication import load_habitica_authentication_credentials
from .configuration import (
    get_configuration,
    get_config_file,
    copy_default_config_to_user_directory,
)
from .dates import parse_date_utc, parse_date_local
from .errors import *
from .habitica_service import HabiticaService
from .iplugin import IPlugin
from .scriptabit import start_cli
from .task import Task, Difficulty, CharacterAttribute
from .task_mapping import TaskMapping
from .task_service import TaskService
from .task_sync import TaskSync
from .utility_functions import UtilityFunctions


from .metadata import __author__, __email__, __version__
