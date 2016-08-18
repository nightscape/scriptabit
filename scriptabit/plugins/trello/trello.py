# -*- coding: utf-8 -*-
""" Synchronisation of Trello cards to Habitica To-Dos.
"""

# Ensure backwards compatibility with Python 2
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals)
from builtins import *
import logging
import os
import pickle
from configparser import ConfigParser, NoOptionError
from datetime import datetime, timedelta

import pytz
import scriptabit
from scriptabit import (
    CharacterAttribute,
    Difficulty,
    HabiticaTaskService,
    TaskMap,
    TaskSync,
    UtilityFunctions)

from trello import TrelloClient
from trello.util import create_oauth_token

from .trello_task_service import TrelloTaskService

class Trello(scriptabit.IPlugin):
    """ Trello card synchronisation.

    Attributes:
        __tc: TrelloClient instance
        __habitica_task_service: The HabiticaTaskService instance
        __task_map_file: = Task mapping data file
        __data_file: Sync data file name
        __data (Trello.PersistentData): Persistent sync data
    """

    class PersistentData(object):
        """ Data that needs to be persisted. """
        last_sync = None

        def __init__(self):
            self.last_sync = datetime.now(tz=pytz.utc) - timedelta(days=2)


    def __init__(self):
        """ Initialises the plugin.
        Generally nothing to do here other than initialise any class attributes.
        """
        super().__init__()
        self.__tc = None
        self.__habitica_task_service = None
        self.__task_map_file = None
        self.__data_file = None
        self.__data = None

    def get_arg_parser(self):
        """Gets the argument parser containing any CLI arguments for the plugin.

        Note that to avoid argument name conflicts, only long argument names
        should be used, and they should be prefixed with the plugin-name or
        unique abbreviation.

        Returns: argparse.ArgParser:  The `ArgParser` containing the argument
        definitions.
        """
        parser = super().get_arg_parser()

        # Boards to sync (empty list for all active boards)
        parser.add(
            '--trello-boards',
            required=False,
            action='append',
            help='''The list of Trello boards to sync. Leave empty to
sync all active boards''')

        # Lists to sync (empty list for all lists in all selected boards)
        parser.add(
            '--trello-lists',
            required=False,
            action='append',
            help='''The Trello lists to sync. Leave empty to
sync all lists on all selected boards''')

        # Lists that mark cards as done
        parser.add(
            '--trello-done-lists',
            required=False,
            action='append',
            help='''The Trello lists that mark cards as complete.
If empty, then cards are only marked done when archived.''')

        # Filename to use as for the persistent task map
        parser.add(
            '--trello-data-file',
            required=False,
            type=str,
            default='trello_habitica_sync_data',
            help='''Filename to use for storing the synchronisation data.''')

        return parser

    def initialise(self, configuration, habitica_service, data_dir):
        """ Initialises the Trello plugin.

        This involves loading the board and list configuration, confirming the
        API key and secret, obtaining the OAuth tokens if required, and
        instantiating the `TrelloClient` instance.

        Args:
            configuration (ArgParse.Namespace): The application configuration.
            habitica_service (scriptabit.HabiticaService): the Habitica
                Service instance.
            data_dir (str): A writeable directory that the plugin can use for
                persistent data.
        """
        super().initialise(configuration, habitica_service, data_dir)

        logging.getLogger(__name__).info(
            'Syncing Trello boards %s',
            configuration.trello_boards)

        logging.getLogger(__name__).info(
            'Syncing Trello lists %s',
            configuration.trello_lists)

        logging.getLogger(__name__).info(
            'Trello done lists %s',
            configuration.trello_done_lists)

        credentials = self.__load_authentication_credentials()

        # Instantiate the Trello Client
        self.__tc = TrelloClient(
            api_key=credentials['apikey'],
            api_secret=credentials['apisecret'],
            token=credentials['token'],
            token_secret=credentials['tokensecret'])

        # instantiate the HabiticaTaskService
        self.__habitica_task_service = HabiticaTaskService(
            habitica_service,
            tags=['Trello'])

        self.__task_map_file = os.path.join(
            self._data_dir,
            self._config.trello_data_file)

        self.__data_file = os.path.join(
            self._data_dir,
            self._config.trello_data_file+'_extra')

        self.__load_persistent_data()

    def __load_persistent_data(self):
        """ Loads the persistent data """
        try:
            with open(self.__data_file, 'rb') as f:
                self.__data = pickle.load(f)
        except:
            self.__data = Trello.PersistentData()

    def __save_persistent_data(self):
        """ Saves the persistent data """
        with open(self.__data_file, 'wb') as f:
            pickle.dump(self.__data, f, pickle.HIGHEST_PROTOCOL)

    def update_interval_minutes(self):
        """ Indicates the required update interval in minutes.

        Returns: float: The required update interval in minutes.
        """
        return 30

    def update(self):
        """ This update method will be called once on every update cycle,
        with the frequency determined by the value returned from
        `update_interval_minutes()`.

        If a plugin implements a single-shot function, then update should
        return `False`.

        Returns: bool: True if further updates are required; False if the plugin
        is finished and the application should shut down.
        """
        # retrieve the boards to sync
        boards = self.__tc.list_boards(board_filter='open')
        sync_boards = [
            b for b in boards if b.name in self._config.trello_boards]

        self.__ensure_labels_exist(sync_boards)

        # Build a list of sync lists by matching the sync
        # list names in each board
        sync_lists = []
        done_lists = []
        for b in sync_boards:
            for l in b.open_lists():
                if l.name in self._config.trello_lists:
                    sync_lists.append(l)
                elif l.name in self._config.trello_done_lists:
                    done_lists.append(l)

        # some additional information on the source boards and lists
        message = 'Syncing the following lists'
        for l in sync_lists:
            message += '\n   {0}.{1}'.format(l.board.name, l.name)
        message += '\nTreating cards in the following lists as completed'
        for l in done_lists:
            message += '\n   {0}.{1}'.format(l.board.name, l.name)
        logging.getLogger(__name__).debug(message)

        # Load the task map from disk
        task_map = TaskMap(self.__task_map_file)

        # Create the services
        source_service = TrelloTaskService(self.__tc, sync_lists, done_lists)

        # synchronise
        sync = TaskSync(
            source_service,
            self.__habitica_task_service,
            task_map,
            last_sync=self.__data.last_sync)

        stats = sync.synchronise(
            clean_orphans=False,
            sync_completed_new_tasks=False)

        self.__notify(stats)

        # Checkpoint the sync data
        task_map.persist(self.__task_map_file)
        self.__data.last_sync = sync.last_sync
        self.__save_persistent_data()

        # return False if finished, and True to be updated again.
        return False

    def __notify(self, sync_stats):
        """ notify the user about the sync stats.

        Args:
            sync_stats (TaskSync.Stats): Stats from the last sync.
        """
        notes = "{0} updated\n{1} completed\n{2} deleted".format(
            sync_stats.updated,
            sync_stats.completed,
            sync_stats.deleted)

        UtilityFunctions.upsert_notification(
            self._hs,
            text='Trello Sync Completed',
            notes=notes,
            heading_level=4)

    @staticmethod
    def __load_authentication_credentials(
            config_file_name='.auth.cfg',
            section='trello'):
        """ Loads authentication credentials from an ini-style
        configuration file.

        Args:
            config_file_name (str): Basename of the configuration file.
            section (str): Configuration file section name.

        Returns: dict: the selected credentials
        """
        config_file_path = os.path.join(
            os.path.expanduser("~"),
            config_file_name)

        logging.getLogger(__name__).info(
            "Loading trello credentials from %s",
            config_file_path)

        if not os.path.exists(config_file_path):
            raise scriptabit.ConfigError(
                "File '{0}' not found".format(config_file_path))

        config = ConfigParser()
        config.read(config_file_path)

        credentials = {
            'apikey': config.get(section, 'apikey'),
            'apisecret': config.get(section, 'apisecret'),
            'token': '',
            'tokensecret': ''}

        try:
            credentials['token'] = config.get(section, 'token')
            credentials['tokensecret'] = config.get(section, 'tokensecret')
        except NoOptionError:
            # If the OAuth tokens are missing, they will get filled in later
            pass

        if not credentials['apikey']:
            raise scriptabit.ConfigError(
                'Trello API key not found in .auth.cfg')

        if not credentials['apisecret']:
            raise scriptabit.ConfigError(
                'Trello API secret not found in .auth.cfg')

        if not credentials['token'] or not credentials['tokensecret']:
            logging.getLogger(__name__).warning('Getting Trello OAuth token')
            access_token = create_oauth_token(
                expiration='never',
                scope='read,write',
                key=credentials['apikey'],
                secret=credentials['apisecret'],
                name='scriptabit',
                output=True)
            credentials['token'] = access_token['oauth_token']
            credentials['tokensecret'] = access_token['oauth_token_secret']

            # Write back to the file
            config_file_path = os.path.join(
                os.path.expanduser("~"),
                '.auth.cfg')
            with open(config_file_path, 'w') as f:
                logging.getLogger(__name__).warning(
                    'Writing Trello OAuth tokens back to .auth.cfg')
                config.set('trello', 'token', credentials['token'])
                config.set(
                    'trello',
                    'tokensecret',
                    credentials['tokensecret'])
                config.write(f)

        return credentials

    @staticmethod
    def __ensure_labels_exist(boards):
        """ Ensures that the Trello labels used to mark task difficulty and
        Habitica character attributes exist.

        Args:
            boards (list): The list of boards that are being synchronised.
        """
        difficulty_labels = [a.name for a in Difficulty]
        attribute_labels = [a.name for a in CharacterAttribute]
        required_labels = difficulty_labels + attribute_labels

        for b in boards:
            for rl in required_labels:
                found = [x for x in b.get_labels() if x.name == rl]
                if not found:
                    logging.getLogger(__name__).info(
                        'Board "%s": Label "%s" not found, creating',
                        b.name,
                        rl)
                    b.add_label(rl, color=None)
