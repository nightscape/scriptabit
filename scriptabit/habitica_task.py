# -*- coding: utf-8 -*-
""" Implements a Habitica synchronisation task.
"""
# Ensure backwards compatibility with Python 2
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals)
from builtins import *

from .task import CharacterAttribute, Difficulty, Task


class HabiticaTask(Task):
    """ Defines a Habitica synchronisation task.
    """

    def __init__(self, task_dict):
        """ Initialise the task.

        Args:
            task_dict (dict): The Habitica task dictionary, as returned by
                HabiticaService.
        """
        super().__init__()
        if not isinstance(task_dict, dict):
            raise TypeError

        self.__task_dict = task_dict
        self.__difficulty = Difficulty.from_value(task_dict['priority'])
        self.__attribute = CharacterAttribute.from_value(task_dict['attribute'])

    @property
    def id(self):
        """ Task id """
        return self.__task_dict['_id']

    @property
    def name(self):
        """ Task name """
        return self.__task_dict['text']

    @name.setter
    def name(self, name):
        """ Task name """
        self.__task_dict['text'] = name

    @property
    def description(self):
        """ Task description """
        return self.__task_dict['notes']

    @description.setter
    def description(self, description):
        """ Task description """
        self.__task_dict['notes'] = description

    @property
    def completed(self):
        """ Task completed """
        return self.__task_dict['completed']

    @completed.setter
    def completed(self, completed):
        """ Task completed """
        self.__task_dict['completed'] = completed

    @property
    def difficulty(self):
        """ Task difficulty """
        return self.__difficulty

    @difficulty.setter
    def difficulty(self, difficulty):
        """ Task difficulty """
        if not isinstance(difficulty, Difficulty):
            raise TypeError
        self.__task_dict['priority'] = difficulty.value
        self.__difficulty = difficulty

    @property
    def attribute(self):
        """ Task character attribute """
        return self.__attribute

    @attribute.setter
    def attribute(self, attribute):
        """ Task character attribute """
        if not isinstance(attribute, CharacterAttribute):
            raise TypeError
        self.__task_dict['attribute'] = attribute.value
        self.__attribute = attribute