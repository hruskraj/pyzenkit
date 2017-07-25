#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Copyright (C) since 2016 Jan Mach <honza.mach.ml@gmail.com>
# Use of this source is governed by the MIT license, see LICENSE file.
#--------------


"""
Implementation of JSON configuration handler.

This module provides following tools and features:

* Simple writing of formated JSON configuration files
* Simple reading of any JSON configuration files
* Reading and merging of multiple JSON configuration files/directories
* Support for comments in JSON files
* JSON schema validation
"""


__author__  = "Jan Mach <honza.mach.ml@gmail.com>"


import os
import json
from jsonschema import Draft4Validator, FormatChecker


class JSONSchemaException(Exception):
    """
    Exception describing JSON schema problems.

    This exception will be thrown, when JSON schema validation fails.
    """

    def __init__(self, errstr, errlist):
        """
        Initialize new exception object with concatenated error string and list
        of all separate errors.

        :param str errstr: Description of the problem.
        :param list errlist: List of all errors as unique items.
        """
        super().__init__()

        self.errstr  = errstr
        self.errlist = errlist

    def __str__(self):
        """
        Operator override for automatic string output.
        """
        return repr(self.errstr)


def sortkey(key):
    """
    Helper method for sorting JSON paths.

    Treat keys as lowercase, prefer keys with less path segments.

    :param str key: Key to be sorted.
    :return: Key in sortable format.
    :rtype: tuple
    """
    return (len(key.path), "/".join(str(key.path)).lower())

def json_default(obj):
    """
    Fallback method for serializing unknown objects into JSON.
    """
    return str(obj)


#-------------------------------------------------------------------------------


def json_dump(data, **kwargs):
    """
    Dump given data structure into JSON string. The ``kwargs`` are directly passed to
    underlying :py:func:`json.dumps`, so the available options are the same.
    However, following option will receive default values when not set:

    * ``sort_keys`` - Will be set to *True* by default.
    * ``indent`` - Will be set to 4 by sefault.
    * ``default`` - Will be set to *_json_default* by default.

    :param data: Data structure to be stored.
    :param kwargs: Optional additional arguments as keywords.
    :return: Data structure as JSON string.
    :rtype: str
    """
    if 'sort_keys' not in kwargs:
        kwargs['sort_keys'] = True
    if 'indent' not in kwargs:
        kwargs['indent'] = 4
    if 'default' not in kwargs:
        kwargs['default'] = json_default
    return json.dumps(data, **kwargs)

def json_save(json_file, data, **kwargs):
    """
    Save data structure into given JSON configuration file. The ``kwargs`` are
    directly passed to underlying :py:func:`json.dumps`, so the available options
    are the same. However, following option will receive default values when not set:

    * ``sort_keys`` - Will be set to *True* by default.
    * ``indent`` - Will be set to 4 by sefault.
    * ``default`` - Will be set to *_json_default* by default.

    :param str json_file: Name of the target JSON file.
    :param data: Data structure to be stored.
    :param kwargs: Optional additional arguments as keywords.
    :return: Always returns ``True``.
    :rtype: bool
    """
    if 'sort_keys' not in kwargs:
        kwargs['sort_keys'] = True
    if 'indent' not in kwargs:
        kwargs['indent'] = 4
    if 'default' not in kwargs:
        kwargs['default'] = json_default
    with open(json_file, "w") as jsf:
        json.dump(data, jsf, **kwargs)
    return True

def json_load(json_file):
    """
    Load contents of given JSON configuration file.

    The JSON syntax is enhanced with support for single line comments ('#','//').

    :param str json_file: Name of the source JSON file.
    :return: Loaded data structure.
    :rtype: dict
    """
    with open(json_file, "r") as jsf:
        contents = "\n".join((line for line in jsf if not line.lstrip().startswith(("#", "//"))))
        return json.loads(contents)

def config_validate(data, schema):
    """
    Perform json schema validation of given object, raise JSONSchemaException
    in case of any validation error.

    :param dict data: Data structure to be validated.
    :param dict schema: JSON schema to validate against.
    :raises TypeError: if the schema has invalid data type.
    :raises JSONSchemaException: if the schema validation fails.
    :return: Always returns ``True`` on success.
    :rtype: bool
    """
    if not isinstance(schema, dict):
        raise TypeError("Schema parameter must be a dictionary structure")

    # Validate the structure of the schema itself.
    Draft4Validator.check_schema(schema)

    # Perform the validation and format errors to be more readable.
    validator = Draft4Validator(schema, format_checker=FormatChecker())
    errors = []
    for error in sorted(validator.iter_errors(data), key=sortkey):
        errors.append(
            "JSON schema validation error: key \"%s\", value \"%s\", expected - %s, error message - %s\n" % (
                u"/".join(str(v) for v in error.path),
                error.instance,
                error.schema.get('description', '(no additional info)'),
                error.message
            )
        )
    # Raise custom exception in case of any error.
    if errors:
        raise JSONSchemaException("\n".join(errors), errors)

    return True

def config_load(config_file, schema = None):
    """
    Load configuration from given JSON configuration file with optional JSON
    schema validation.

    :param str config_file: Name of the source JSON config file to be loaded.
    :param schema: Schema can be either ``bool``, ``str``, or ``dict``. If the
                   schema is boolean, generate the name of the schema file from
                   the name of configuration file by appending ``.schema`` suffix.
                   If the schema parameter is string and it is the name of
                   existing directory, look for appropriate schema file in that
                   directory. If the schema parameter is string and it is the name of
                   existing file, load the schema definitions from that file. If
                   the schema is ``dict``, treat it as a JSON schema structure
                   and directly perform validation.
    :raises TypeError: if the schema has invalid data type.
    :return: Loaded data structure.
    :rtype: dict
    """
    data = json_load(config_file)

    # Schema validation is optional.
    if schema:
        # If the schema parameter is boolean, generate the name of the schema
        # file from the name of configuration file by appending ``.schema`` suffix.
        if isinstance(schema, bool):
            schema = "{}.schema".format(config_file)

        if isinstance(schema, str):
            # If the schema parameter is string and it is the name of
            # existing directory, look for appropriate schema file in that
            # directory.
            if os.path.isdir(schema):
                schema = os.path.join(schema, "{}.schema".format(os.path.basename(config_file)))

            # If the schema parameter is string and it is the name of
            # existing file, load the schema definitions from that file.
            if os.path.isfile(schema):
                schema = json_load(schema)

        if not isinstance(schema, dict):
            raise TypeError("Schema parameter must be either boolean, string name of schema file or directory, or dictionary structure")

        config_validate(data, schema)

    return data

def config_load_n(config_files, schema = None):
    """
    Load configuration from multiple JSON configuration files with optional JSON
    schema validation. Merges all loaded configurations into single ``dict``, so
    the order of files matters and it is possible to overwrite previously defined
    keys.

    .. warning::

        The merge is done using :py:func:``dict.update`` method and occurs only
        at highest level.

    :param str config_files: List of names of the source JSON config files to be loaded.
    :param schema: Schema can be either ``bool``, ``str``, or ``dict``. If the
                   schema is boolean, generate the name of the schema file from
                   the name of configuration file by appending ``.schema`` suffix.
                   If the schema parameter is string and it is the name of
                   existing directory, look for appropriate schema file in that
                   directory. If the schema parameter is string and it is the name of
                   existing file, load the schema definitions from that file. If
                   the schema is ``dict``, treat it as a JSON schema structure
                   and directly perform validation.
    :raises TypeError: if the schema has invalid data type.
    :return: Loaded data structure.
    :rtype: dict
    """
    data = {}
    for cfn in config_files:
        cfg = config_load(cfn, schema = schema)
        data.update((key, val) for key, val in cfg.items() if val is not None)
    return data

def config_load_dir(config_dir, schema = None, extension = '.json.conf'):
    """
    Load configuration from all JSON configuration files found within given
    configuration directory with optional JSON schema validation. Merges all
    loaded configurations into single ``dict``, so the order of files matters
    and it is possible to overwrite previously defined keys.

    .. warning::

        The merge is done using :py:func:``dict.update`` method and occurs only
        at highest level.

    :param str config_dir: Names of the configuration directory.
    :param schema: Schema can be either ``bool``, ``str``, or ``dict``. If the
                   schema is boolean, generate the name of the schema file from
                   the name of configuration file by appending ``.schema`` suffix.
                   If the schema parameter is string and it is the name of
                   existing directory, look for appropriate schema file in that
                   directory. If the schema parameter is string and it is the name of
                   existing file, load the schema definitions from that file. If
                   the schema is ``dict``, treat it as a JSON schema structure
                   and directly perform validation.
    :param str extension: Config file name extension for lookup function.
    :raises TypeError: if the schema has invalid data type.
    :return: Loaded data structure.
    :rtype: dict
    """
    config_files = []
    all_files = os.listdir(config_dir)
    for afn in sorted(all_files):
        afp = os.path.join(config_dir, afn)
        if not os.path.isfile(afp):
            continue
        if not afp.endswith(extension):
            continue
        config_files.append(afp)
    return config_load_n(config_files, schema)


#-------------------------------------------------------------------------------

#
# Perform the demonstration.
#
if __name__ == "__main__":

    #import pprint

    print("Loading single JSON config file:")
    #cfg_a = config_load("/tmp/demo.pyzenkit.jsonconf.json")
    #pprint.pprint(cfg_a)

    print("Loading single JSON config file with autovalidation:")
    #cfg_a = config_load("/tmp/demo.pyzenkit.jsonconf.json", schema = True)
    #pprint.pprint(cfg_a)

    print("Loading JSON config directory:")
    #cfg_b = config_load_dir("/tmp/demo.pyzenkit.jsonconf/")
    #pprint.pprint(cfg_b)

    print("Loading JSON config directory with autovalidation:")
    #cfg_b = config_load_dir("/tmp/demo.pyzenkit.jsonconf/", schema = True)
    #pprint.pprint(cfg_b)
