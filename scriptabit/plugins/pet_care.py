# -*- coding: utf-8 -*-
""" Habitica pet care.

Options for batch hatching and feeding pets.
"""
# Ensure backwards compatibility with Python 2
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals)
from builtins import *
import logging
from pprint import pprint
from time import sleep

import scriptabit


class PetCare(scriptabit.IPlugin):
    """ Habitica pet care
    """
    def __init__(self):
        """ Initialises the plugin.
        """
        super().__init__()
        self.__items = None
        self.__print_help = None
        self.__any_food = False

        # Generate the reference lists
        self.__base_pets = [
            'BearCub',
            'Cactus',
            'Dragon',
            'FlyingPig',
            'Fox',
            'LionCub',
            'PandaCub',
            'TigerCub',
            'Wolf',
        ]

        # TODO: other rare pets
        self.__rare_pets = [
            'Wolf-Veteran',
        ]

        # I don't need this list. Any pet that is not in the base pets,
        # special potions, or rare list is by default a quest pet
        # self.__quest_pets = [
            # 'Armadillo',
            # 'SeaTurtle',
            # 'Axolotl',
            # 'Treeling',
            # 'Falcon',
            # 'Snail',
            # 'Monkey',
            # 'Sabretooth',
            # 'Unicorn',
            # 'Snake',
            # 'Frog',
            # 'Horse',
            # 'Cheetah',
            # '',
            # '',
            # '',
            # '',
            # '',
            # '',
        # ]

        self.__preferred_foods = {
            'Base': ['Meat'],
            'CottonCandyBlue': ['CottonCandyBlue'],
            'CottonCandyPink': ['CottonCandyPink'],
            'Desert': ['Potatoe'],
            'Golden': ['Honey'],
            'Red': ['Strawberry'],
            'Skeleton': ['Fish'],
            'White': ['Milk'],
            'Zombie': ['RottenMeat'],
            'Shade': ['Chocolate'],
        }

        self.__base_potions = [
            'Base',
            'White',
            'Desert',
            'Red',
            'Shade',
            'Skeleton',
            'Zombie',
            'CottonCandyPink',
            'CottonCandyBlue',
            'Golden',
        ]

        self.__special_potions = [
            'Floral',
            'Thunderstorm',
        ]

        # augment the preferred foods with the special foods
        for potion in self.__base_potions:
            self.__preferred_foods[potion].append('Cake_{0}'.format(potion))
            # TODO: other special foods

        # build a list of all foods, for the special potions
        self.__all_foods = []
        for f in self.__preferred_foods.values():
            self.__all_foods.extend(f)

        for potion in self.__special_potions:
            self.__preferred_foods[potion] = self.__all_foods

    def get_arg_parser(self):
        """Gets the argument parser containing any CLI arguments for the plugin.

        Returns: argparse.ArgParser:  The `ArgParser` containing the argument
        definitions.
        """
        parser = super().get_arg_parser()

        parser.add(
            '--pets-list-items',
            required=False,
            action='store_true',
            help='Lists all pet-related items')

        parser.add(
            '--pets-feed',
            required=False,
            action='store_true',
            help='Feed all pets')

        parser.add(
            '--pets-any-food',
            required=False,
            action='store_true',
            help='When feeding pets, allows the use of non-preferred food')

        parser.add(
            '--no-base-pets',
            required=False,
            action='store_true',
            help='Disables feeding of base pets')

        parser.add(
            '--quest-pets',
            required=False,
            action='store_true',
            help='Allows feeding of quest pets')

        parser.add(
            '--magic-pets',
            required=False,
            action='store_true',
            help='Allows feeding of magic pets')

        self.__print_help = parser.print_help

        return parser

    def initialise(self, configuration, habitica_service, data_dir):
        """ Initialises the plugin.

        Generally, any initialisation should be done here rather than in
        activate or __init__.

        Args:
            configuration (ArgParse.Namespace): The application configuration.
            habitica_service: the Habitica Service instance.
            data_dir (str): A writeable directory that the plugin can use for
                persistent data.
        """
        super().initialise(configuration, habitica_service, data_dir)
        logging.getLogger(__name__).info('Scriptabit Pet Care Services: looking'
                                         ' after your pets since yesterday')

        self.__items = self._hs.get_user()['items']
        self.__any_food = self._config.pets_any_food

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

        # do work here
        if self._config.pets_list_items:
            self.list_pet_items(self.__items)
            return False

        if self._config.pets_feed:
            self.feed_pets()
            return False

        # if no other options selected, print plugin specific help and exit
        self.__print_help()

        # return False if finished, and True to be updated again.
        return False

    def is_base_pet(self, pet, animal, potion):
        """ Is this a base pet?

        Args:
            pet (str): The full pet name.
            animal (str): The animal type.
            potion (str): The potion type.
        """
        return animal in self.__base_pets and potion in self.__base_potions

    def is_quest_pet(self, pet, animal, potion):
        """ Is this a quest pet?

        Args:
            pet (str): The full pet name.
            animal (str): The animal type.
            potion (str): The potion type.
        """
        return not (self.is_base_pet(pet, animal, potion)
                    or self.is_magic_pet(pet, animal, potion)
                    or self.is_rare_pet(pet, animal, potion))

    def is_magic_pet(self, pet, animal, potion):
        """ Is this a magic pet?

        Args:
            pet (str): The full pet name.
            animal (str): The animal type.
            potion (str): The potion type.
        """
        return potion in self.__special_potions

    def is_rare_pet(self, pet, animal, potion):
        """ Is this a rare pet?

        Args:
            pet (str): The full pet name.
            animal (str): The animal type.
            potion (str): The potion type.
        """
        return pet in self.__rare_pets

    def get_pets(self, base=True, magic=False, quest=False, rare=False):
        """ Gets a filtered list of current user pets.

        Args:
            base (bool): Includes or excludes base pets.
            magic (bool): Includes or excludes magic pets.
            quest (bool): Includes or excludes quest pets.
            rare (bool): Includes or excludes rare pets.

        Returns:
            list: the filtered pet list.
        """
        pets = []
        for pet, growth in self.__items['pets'].items():
            # Habitica indicates a pet that has been raised to a mount with
            # growth == -1. These pets are non-interactive, so exclude them
            if growth > 0:
                animal, potion = pet.split('-')
                if base and self.is_base_pet(pet, animal, potion):
                    pets.append(pet)
                elif magic and self.is_magic_pet(pet, animal, potion):
                    pets.append(pet)
                elif quest and self.is_quest_pet(pet, animal, potion):
                    pets.append(pet)
                elif rare and self.is_rare_pet(pet, animal, potion):
                    pets.append(pet)

        return pets

    def feed_pets(self):
        """ Feeds all current pets. """
        # TODO: This algorithm is ugly, but it works.
        # I think a version built around a food generator might be more elegant.
        # The generator would keep returning an in-stock food item suitable for
        # a given pet until no more suitable foods are in stock.
        # Could then loop until the food is gone, or the pet becomes a mount.

        pets = self.get_pets(
            base=not self._config.no_base_pets,
            magic=self._config.magic_pets,
            quest=self._config.quest_pets,
            rare=False)

        for pet in pets:
            try:
                food = self.get_food_for_pet(pet)
                while food:
                    response = self._hs.feed_pet(pet, food)
                    self.consume_food(food)
                    growth = response['data']
                    logging.getLogger(__name__).info(
                        '%s (%d): %s', pet, growth, response['message'])

                    if growth > 0:
                        # growth > 0 indicates that the pet is still hungry
                        food = self.get_food_for_pet(pet)
                    else:
                        # growth <= 0 (-1 actually) indicates that the
                        # pet became a mount
                        break

                logging.getLogger(__name__).info('Fetching the next pet ...')
                sleep(2)
            except Exception as e:
                logging.getLogger(__name__).warning(e)

    def get_food_for_pet(self, pet):
        """ Gets a food item for a pet

        Args:
            pet (str): The composite pet name (animal-potion)

        Returns:
            str: The name of a suitable food if that food is in stock.
                If no suitable food is available, then None is returned.
        """
        # split the pet name
        _, potion = pet.split('-')

        if self.__any_food:
            for food, quantity in self.__items['food']:
                if quantity > 0:
                    return food
        else:
            for food in self.__preferred_foods[potion]:
                if self.has_food(food):
                    return food
        return None

    def has_food(self, food):
        """ Returns True if the food is in stock, otherwise False.

        Args:
            food (str): The food to check

        Returns:
            bool: True if the food is in stock, otherwise False.
        """
        return self.__items['food'].get(food, 0) > 0

    def consume_food(self, food):
        """ Consumes a food, updating the cached quantity.

        Args:
            food (str): The food.
        """
        quantity = self.__items['food'].get(food, 0)
        if quantity > 0:
            self.__items['food'][food] = quantity - 1

    @staticmethod
    def list_pet_items(items):
        """ Lists all pet-related inventory items.

        Args:
            items (dict): The Habitica user.items dictionary.
        """
        print()
        print('Food:')
        pprint(items['food'])
        print()
        print('Eggs:')
        pprint(items['eggs'])
        print()
        print('Hatching potions:')
        pprint(items['hatchingPotions'])
        print()
        print('Pets:')
        pprint(items['pets'])
        print()
        print('Mounts:')
        pprint(items['mounts'])
