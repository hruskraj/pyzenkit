#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Copyright (C) since 2016 Jan Mach <honza.mach.ml@gmail.com>
# Use of this source is governed by the MIT license, see LICENSE file.
#-------------------------------------------------------------------------------

import unittest
from unittest.mock import Mock, MagicMock, call
from pprint import pformat, pprint

import os
import sys
import shutil
import collections

# Generate the path to custom 'lib' directory
lib = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, lib)

import pyzenkit.jsonconf

SPOOL_DIR = '/tmp/test.pyzenkit.jsonconf'

TEST_DATA = [
    {
        "f": 'a.json.conf',
        "d": {"x": 1, "y": 2, "z": 3},
        "s": {
            "$schema": "http://json-schema.org/schema#",
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "z": {"type": "integer"}
            },
            "required": ["x","y","z"]
        }
    },
    {
        "f": 'b.json.conf',
        "d": {"a": 1, "b": 2, "c": 3, "x": 100},
        "s": {
            "$schema": "http://json-schema.org/schema#",
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
                "c": {"type": "integer"}
            },
            "required": ["a","b","c"]
        }
    },
    {
        "f": 'test.json',
        "d": {"hello": 1, "world": 2},
        "s": {
            "$schema": "http://json-schema.org/schema#",
            "type": "object",
            "properties": {
                "hello": {"type": "integer"},
                "world": {"type": "integer"}
            },
            "required": ["hello","world"]
        }
    }
]

class TestPyzenkitJsonconf(unittest.TestCase):

    def setUp(self):
        try:
            os.mkdir(SPOOL_DIR)
            for t in TEST_DATA:
                pyzenkit.jsonconf.json_save(
                    os.path.join(SPOOL_DIR, t['f']),
                    t['d']
                )
                pyzenkit.jsonconf.json_save(
                    os.path.join(SPOOL_DIR, '{}.schema'.format(t['f'])),
                    t['s']
                )
        except FileExistsError:
            pass
    def tearDown(self):
        shutil.rmtree(SPOOL_DIR)

    def test_01_json_save(self):
        """
        Test the JSON saving.
        """
        pyzenkit.jsonconf.json_save(
                os.path.join(SPOOL_DIR, 'save-test.json'),
                {"x": 1, "y": 2, "z": 3}
            )
        self.assertTrue(os.path.isfile(os.path.join(SPOOL_DIR, 'save-test.json')))

    def test_02_json_load(self):
        """
        Test the JSON loading.
        """
        # Attempt to load missing JSON file
        self.assertRaises(FileNotFoundError, pyzenkit.jsonconf.json_load, os.path.join(SPOOL_DIR, 'bogus.json'))

        # Attempt to load existing JSON files
        self.assertEqual(pyzenkit.jsonconf.json_load(os.path.join(SPOOL_DIR, 'a.json.conf')), {"x": 1, "y": 2, "z": 3})
        self.assertEqual(pyzenkit.jsonconf.json_load(os.path.join(SPOOL_DIR, 'b.json.conf')), {"a": 1, "b": 2, "c": 3, "x": 100})
        self.assertEqual(pyzenkit.jsonconf.json_load(os.path.join(SPOOL_DIR, 'test.json')), {"hello": 1, "world": 2})

    def test_03_config_validate(self):
        """
        Test the JSON validations.
        """
        # Test direct validation by passing schema as object structure
        self.assertTrue(pyzenkit.jsonconf.config_validate(
            {
                "x": 1,
                "y": 2,
                "z": 3
            },
            schema = TEST_DATA[0]['s']
        ))
        # Test validation of invalid data structure
        self.assertRaises(pyzenkit.jsonconf.JSONSchemaException, pyzenkit.jsonconf.config_validate,
            {
                "x": 1,
                "y": 2
            },
            schema = TEST_DATA[0]['s']
        )

    def test_04_config_load(self):
        """
        Test config file loading.
        """
        # Attempt to load missing JSON config file
        self.assertRaises(FileNotFoundError, pyzenkit.jsonconf.config_load, os.path.join(SPOOL_DIR, 'bogus.json'))

        # Attempt to load existing JSON config files
        self.assertEqual(pyzenkit.jsonconf.config_load(os.path.join(SPOOL_DIR, 'a.json.conf'), ), {"x": 1, "y": 2, "z": 3})
        self.assertEqual(pyzenkit.jsonconf.config_load(os.path.join(SPOOL_DIR, 'b.json.conf')), {"a": 1, "b": 2, "c": 3, "x": 100})
        self.assertEqual(pyzenkit.jsonconf.config_load(os.path.join(SPOOL_DIR, 'test.json')), {"hello": 1, "world": 2})

        # Attempt to load existing JSON config files and perform validation with
        # schema given as dictionary structure
        self.assertEqual(pyzenkit.jsonconf.config_load(os.path.join(SPOOL_DIR, 'a.json.conf'), schema = TEST_DATA[0]['s']), {"x": 1, "y": 2, "z": 3})

        # Attempt to load existing JSON config files and perform validation with
        # schema given as string name of schema file
        self.assertEqual(pyzenkit.jsonconf.config_load(os.path.join(SPOOL_DIR, 'b.json.conf'), schema = os.path.join(SPOOL_DIR, 'b.json.conf.schema')), {"a": 1, "b": 2, "c": 3, "x": 100})

        # Attempt to load existing JSON config files and perform validation with
        # schema given as string name of schema directory
        self.assertEqual(pyzenkit.jsonconf.config_load(os.path.join(SPOOL_DIR, 'b.json.conf'), schema = SPOOL_DIR), {"a": 1, "b": 2, "c": 3, "x": 100})

        # Attempt to load existing JSON config files and perform validation with
        # schema given as boolean (let the code pick appripriate schema file)
        self.assertEqual(pyzenkit.jsonconf.config_load(os.path.join(SPOOL_DIR, 'test.json'), schema = True), {"hello": 1, "world": 2})

    def test_05_config_load_n(self):
        """
        Test loading of multiple config files.
        """
        self.assertEqual(pyzenkit.jsonconf.config_load_n([
            os.path.join(SPOOL_DIR, 'a.json.conf'),
            os.path.join(SPOOL_DIR, 'b.json.conf'),
            os.path.join(SPOOL_DIR, 'test.json')]), {"a": 1, "b": 2, "c": 3, "x": 100, "y": 2, "z": 3, "hello": 1, "world": 2})
        self.assertEqual(pyzenkit.jsonconf.config_load_n([
            os.path.join(SPOOL_DIR, 'a.json.conf'),
            os.path.join(SPOOL_DIR, 'b.json.conf'),
            os.path.join(SPOOL_DIR, 'test.json')], schema = SPOOL_DIR), {"a": 1, "b": 2, "c": 3, "x": 100, "y": 2, "z": 3, "hello": 1, "world": 2})
        self.assertEqual(pyzenkit.jsonconf.config_load_n([
            os.path.join(SPOOL_DIR, 'a.json.conf'),
            os.path.join(SPOOL_DIR, 'b.json.conf'),
            os.path.join(SPOOL_DIR, 'test.json')], schema = True), {"a": 1, "b": 2, "c": 3, "x": 100, "y": 2, "z": 3, "hello": 1, "world": 2})

    def test_06_config_load_n(self):
        """
        Test loading of config files within configuration directory.
        """
        self.assertEqual(pyzenkit.jsonconf.config_load_dir(SPOOL_DIR), {"a": 1, "b": 2, "c": 3, "x": 100, "y": 2, "z": 3})
        self.assertEqual(pyzenkit.jsonconf.config_load_dir(SPOOL_DIR, schema = SPOOL_DIR), {"a": 1, "b": 2, "c": 3, "x": 100, "y": 2, "z": 3})
        self.assertEqual(pyzenkit.jsonconf.config_load_dir(SPOOL_DIR, schema = True), {"a": 1, "b": 2, "c": 3, "x": 100, "y": 2, "z": 3})

        self.assertEqual(pyzenkit.jsonconf.config_load_dir(SPOOL_DIR, extension = '.json'), {"hello": 1, "world": 2})
        self.assertEqual(pyzenkit.jsonconf.config_load_dir(SPOOL_DIR, schema = SPOOL_DIR, extension = '.json'), {"hello": 1, "world": 2})
        self.assertEqual(pyzenkit.jsonconf.config_load_dir(SPOOL_DIR, schema = True, extension = '.json'), {"hello": 1, "world": 2})

if __name__ == "__main__":
    unittest.main()

