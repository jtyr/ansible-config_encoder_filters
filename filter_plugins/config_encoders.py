# (c) 2016, Jiri Tyr <jiri.tyr@gmail.com>
#
# This file is part of Config Encoder Filters (CEF)
#
# CEF is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CEF is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CEF.  If not, see <http://www.gnu.org/licenses/>.

"""
Config Encoder Filters

More information: https://github.com/jtyr/ansible-config_encoder_filters
"""

from __future__ import (absolute_import, division, print_function)
from ansible.module_utils.six import string_types
from ansible import errors
from copy import copy
import re


def _str_is_bool(data):
    """Verify if data is boolean."""

    return re.match(r"^(true|false)$", str(data), flags=re.IGNORECASE)


def _str_is_int(data):
    """Verify if data is integer."""

    return re.match(r"^[-+]?(0|[1-9][0-9]*)$", str(data))


def _str_is_float(data):
    """Verify if data is float."""

    return re.match(
        r"^[-+]?(0|[1-9][0-9]*)(\.[0-9]*)?(e[-+]?[0-9]+)?$",
        str(data), flags=re.IGNORECASE)


def _str_is_num(data):
    """Verify if data is either integer or float."""

    return _str_is_int(data) or _str_is_float(data)


def _is_num(data):
    """Verify if data is either int or float.

    Could be replaced by:

        from numbers import Number as number
        isinstance(data, number)

    but that requires Python v2.6+.
    """

    return isinstance(data, int) or isinstance(data, float)


def _escape(data, quote='"', format=None):
    """Escape special characters in a string."""

    if format == 'xml':
        return (
            str(data).
            replace('&', '&amp;').
            replace('<', '&lt;').
            replace('>', '&gt;'))
    elif format == 'control':
        return (
            str(data).
            replace('\b', '\\b').
            replace('\f', '\\f').
            replace('\n', '\\n').
            replace('\r', '\\r').
            replace('\t', '\\t'))
    elif quote is not None and len(quote):
        return str(data).replace('\\', '\\\\').replace(quote, "\\%s" % quote)
    else:
        return data


def encode_apache(
        data, block_type='sections', convert_bools=False, convert_nums=False,
        indent="  ", level=0, quote_all_nums=False, quote_all_strings=False):
    """Convert Python data structure to Apache format."""

    # Return value
    rv = ""

    if block_type == 'sections':
        for c in data['content']:
            # First check if this section has options
            if 'options' in c:
                rv += encode_apache(
                    c['options'],
                    convert_bools=convert_bools,
                    convert_nums=convert_nums,
                    indent=indent,
                    level=level+1,
                    quote_all_nums=quote_all_nums,
                    quote_all_strings=quote_all_strings,
                    block_type='options')

            is_empty = False

            # Check if this section has some sub-sections
            if 'sections' in c:
                for s in c['sections']:
                    # Check for empty sub-sections
                    for i in s['content']:
                        if (
                                ('options' in i and len(i['options']) > 0) or
                                ('sections' in i and len(i['sections']) > 0)):
                            is_empty = True

                    if is_empty:
                        rv += "%s<%s" % (indent * level, s['name'])

                        if 'operator' in s:
                            rv += " %s" % s['operator']

                        if 'param' in s:
                            rv += ' '
                            rv += encode_apache(
                                s['param'],
                                convert_bools=convert_bools,
                                convert_nums=convert_nums,
                                indent=indent,
                                level=level+1,
                                quote_all_nums=quote_all_nums,
                                quote_all_strings=quote_all_strings,
                                block_type='value')

                        rv += ">\n"
                        rv += encode_apache(
                            s,
                            convert_bools=convert_bools,
                            convert_nums=convert_nums,
                            indent=indent,
                            level=level+1,
                            quote_all_nums=quote_all_nums,
                            quote_all_strings=quote_all_strings,
                            block_type='sections')
                        rv += "%s</%s>\n" % (indent * level, s['name'])

                        # If not last item of the loop
                        if c['sections'][-1] != s:
                            rv += "\n"

            if (
                    data['content'][-1] != c and (
                        'options' in c and len(c['options']) > 0 or (
                            'sections' in c and
                            len(c['sections']) > 0 and
                            is_empty))):
                rv += "\n"

    elif block_type == 'options':
        for o in data:
            for key, val in sorted(o.items()):
                rv += "%s%s " % (indent * (level-1), key)
                rv += encode_apache(
                    val,
                    convert_bools=convert_bools,
                    convert_nums=convert_nums,
                    indent=indent,
                    level=level+1,
                    quote_all_nums=quote_all_nums,
                    quote_all_strings=quote_all_strings,
                    block_type='value')
                rv += "\n"

    elif block_type == 'value':
        if isinstance(data, bool) or convert_bools and _str_is_bool(data):
            # Value is a boolean

            rv += str(data).lower()

        elif (
                _is_num(data) or
                (convert_nums and _str_is_num(data))):
            # Value is a number

            if quote_all_nums:
                rv += '"%s"' % data
            else:
                rv += str(data)

        elif isinstance(data, string_types):
            # Value is a string
            if (
                    quote_all_strings or
                    " " in data or
                    "\t" in data or
                    "\n" in data or
                    "\r" in data or
                    data == ""):

                rv += '"%s"' % _escape(data)
            else:
                rv += data

        elif isinstance(data, list):
            # Value is a list
            for v in data:
                rv += encode_apache(
                    v,
                    convert_bools=convert_bools,
                    convert_nums=convert_nums,
                    indent=indent,
                    level=level+1,
                    quote_all_nums=quote_all_nums,
                    quote_all_strings=quote_all_strings,
                    block_type='value')

                # If not last item of the loop
                if data[-1] != v:
                    rv += " "

    return rv


def encode_erlang(
        data, atom_value_indicator=":", convert_bools=False,
        convert_nums=False, indent="  ", level=0, ordered_tuple_indicator=":"):
    """Convert Python data structure to Erlang format."""

    # Return value
    rv = ""

    if isinstance(data, dict):
        # It's a dict

        rv += "\n"

        for key, val in sorted(data.items()):
            if key == ordered_tuple_indicator:
                rv += "%s{" % (indent*level)

                if isinstance(val, list):
                    for i, v in enumerate(val):
                        rv += encode_erlang(
                            v,
                            atom_value_indicator=atom_value_indicator,
                            convert_bools=convert_bools,
                            convert_nums=convert_nums,
                            indent=indent,
                            level=level+1,
                            ordered_tuple_indicator=ordered_tuple_indicator)

                        if i+1 < len(val):
                            rv += ", "
            else:
                rv += "%s{%s," % (indent*level, key)

                if not isinstance(val, dict):
                    rv += " "

                rv += encode_erlang(
                    val,
                    atom_value_indicator=atom_value_indicator,
                    convert_bools=convert_bools,
                    convert_nums=convert_nums,
                    indent=indent,
                    level=level+1,
                    ordered_tuple_indicator=ordered_tuple_indicator)

            rv += "}"
    elif (
            data == "null" or
            _is_num(data) or
            isinstance(data, bool) or
            (convert_nums and _str_is_num(data)) or
            (convert_bools and _str_is_bool(data))):
        # It's null, number or boolean

        rv += str(data).lower()

    elif isinstance(data, string_types):
        # It's a string

        atom_len = len(atom_value_indicator)

        if (
                len(data) > atom_len and
                data[0:atom_len] == atom_value_indicator):

            # Atom configuration value
            rv += data[atom_len:]
        else:
            rv += '"%s"' % _escape(data)

    else:
        # It's a list

        rv += "["

        for val in data:
            if (
                    isinstance(val, string_types) or
                    _is_num(val)):
                rv += "\n%s" % (indent*level)

            rv += encode_erlang(
                val,
                atom_value_indicator=atom_value_indicator,
                convert_bools=convert_bools,
                convert_nums=convert_nums,
                indent=indent,
                level=level+1,
                ordered_tuple_indicator=ordered_tuple_indicator)

            if data[-1] == val:
                # Last item of the loop
                rv += "\n"
            else:
                rv += ","

        if len(data) > 0:
            rv += "%s]" % (indent * (level-1))
        else:
            rv += "]"

        if level == 0:
            rv += ".\n"

    return rv


def encode_haproxy(data, indent="  "):
    """Convert Python data structure to HAProxy format."""

    # Return value
    rv = ""
    # Indicates first loop
    first = True
    # Indicates whether the previous section was a comment
    prev_comment = False

    for section in data:
        if first:
            first = False
        elif prev_comment:
            prev_comment = False
        else:
            # Print empty line between sections
            rv += "\n"

        if isinstance(section, dict):
            # It's a section
            rv += "%s\n" % list(section.keys())[0]

            # Process all parameters of the section
            for param in list(section.values())[0]:
                if isinstance(param, dict):
                    for p_val in list(param.values())[0]:
                        if len(p_val) > 0:
                            rv += "%s%s %s\n" % (
                                indent, list(param.keys())[0], p_val)
                else:
                    if len(param) > 0:
                        rv += "%s%s\n" % (indent, param)
        else:
            # It's a comment of a parameter
            rv += "%s\n" % section
            prev_comment = True

    return rv


def encode_ini(
        data, comment="#", delimiter="=", indent="", quote="",
        section_is_comment=False, ucase_prop=False):
    """Convert Python data structure to INI format."""

    # Return value
    rv = ""

    # First process all standalone properties
    for prop, val in sorted(data.items()):
        if ucase_prop:
            prop = prop.upper()

        vals = []

        if isinstance(val, list):
            vals = val
        elif not isinstance(val, dict):
            vals = [val]

        for item in vals:
            if (
                    len(quote) == 0 and
                    isinstance(item, string_types) and
                    len(item) == 0):
                item = '""'

            if item is not None:
                if item == "!!!null":
                    rv += "%s%s\n" % (indent, prop)
                else:
                    rv += "%s%s%s%s%s%s\n" % (
                        indent, prop, delimiter, quote, _escape(item, quote),
                        quote)

    # Then process all sections
    for section, props in sorted(data.items()):
        if isinstance(props, dict):
            if rv != "":
                rv += "\n"

            if section_is_comment:
                rv += "%s %s\n" % (comment, section)
            else:
                rv += "[%s]\n" % (section)

            # Let process all section options as standalone properties
            rv += encode_ini(
                props,
                delimiter=delimiter,
                indent=indent,
                quote=quote,
                section_is_comment=section_is_comment,
                ucase_prop=ucase_prop)

    return rv


def encode_json(
        data, convert_bools=False, convert_nums=False, indent="  ", level=0):
    """Convert Python data structure to JSON format."""

    # Return value
    rv = ""

    if isinstance(data, dict):
        # It's a dict

        rv += "{"

        if len(data) > 0:
            rv += "\n"

        items = sorted(data.items())

        for key, val in items:
            rv += '%s"%s": ' % (indent * (level+1), key)
            rv += encode_json(
                val,
                convert_bools=convert_bools,
                convert_nums=convert_nums,
                indent=indent,
                level=level+1)

            # Last item of the loop
            if items[-1] == (key, val):
                rv += "\n"
            else:
                rv += ",\n"

        if len(data) > 0:
            rv += "%s}" % (indent * level)
        else:
            rv += "}"

        if level == 0:
            rv += "\n"

    elif (
            data == "null" or
            _is_num(data) or
            (convert_nums and _str_is_num(data)) or
            (convert_bools and _str_is_bool(data))):
        # It's a number, null or boolean

        rv += str(data).lower()

    elif isinstance(data, string_types):
        # It's a string

        rv += '"%s"' % _escape(_escape(data), format='control')

    else:
        # It's a list

        rv += "["

        if len(data) > 0:
            rv += "\n"

        for val in data:
            rv += indent * (level+1)
            rv += encode_json(
                val,
                convert_bools=convert_bools,
                convert_nums=convert_nums,
                indent=indent,
                level=level+1)

            # Last item of the loop
            if data[-1] == val:
                rv += "\n"
            else:
                rv += ",\n"

        if len(data) > 0:
            rv += "%s]" % (indent * level)
        else:
            rv += "]"

    return rv


def encode_logstash(
        data, backslash_ignore_prefix='@@@', convert_bools=False,
        convert_nums=False, indent="  ", level=0, prevtype="",
        section_prefix=":"):
    """Convert Python data structure to Logstash format."""

    # Return value
    rv = ""

    if isinstance(data, dict):
        # The item is a dict

        if prevtype in ('value', 'value_hash', 'array'):
            rv += "{\n"

        items = sorted(data.items())

        for key, val in items:
            if key[0] == section_prefix:
                rv += "%s%s {\n" % (indent * level, key[1:])
                rv += encode_logstash(
                    val,
                    convert_bools=convert_bools,
                    convert_nums=convert_nums,
                    indent=indent,
                    level=level+1,
                    prevtype='block')

                # Last item of the loop
                if items[-1] == (key, val):
                    if (
                            isinstance(val, string_types) or
                            _is_num(val) or
                            isinstance(val, bool) or (
                                isinstance(val, dict) and
                                val and
                                list(val.keys())[0][0] != section_prefix)):
                        rv += "\n%s}\n" % (indent * level)
                    else:
                        rv += "%s}\n" % (indent * level)
            else:
                rv += indent * level

                if prevtype == 'value_hash':
                    rv += '"%s" => ' % key
                else:
                    rv += "%s => " % key

                rv += encode_logstash(
                    val,
                    convert_bools=convert_bools,
                    convert_nums=convert_nums,
                    indent=indent,
                    level=level+1,
                    prevtype=(
                        'value_hash' if isinstance(val, dict) else 'value'))

            if (
                    items[-1] != (key, val) and (
                        isinstance(val, string_types) or
                        _is_num(val) or
                        isinstance(val, bool))):
                rv += "\n"

        if prevtype in ('value', 'value_hash', 'array'):
            rv += "\n%s}" % (indent * (level-1))

            if prevtype in ('value', 'value_array'):
                rv += "\n"

    elif (
            _is_num(data) or
            isinstance(data, bool) or
            (convert_nums and _str_is_num(data)) or
            (convert_bools and _str_is_bool(data))):
        # It's number or boolean

        rv += str(data).lower()

    elif isinstance(data, string_types):
        # It's a string

        if data.startswith(backslash_ignore_prefix):
            rv += "%s" % data[len(backslash_ignore_prefix):]
        else:
            rv += '"%s"' % _escape(data)

    else:
        # It's a list

        for val in data:
            if isinstance(val, dict) and list(
                    val.keys())[0][0] == section_prefix:
                # Value is a block

                rv += encode_logstash(
                    val,
                    convert_bools=convert_bools,
                    convert_nums=convert_nums,
                    indent=indent,
                    level=level,
                    prevtype='block')
            else:
                # First item of the loop
                if data[0] == val:
                    rv += "[\n"

                rv += indent * level
                rv += encode_logstash(
                    val,
                    convert_bools=convert_bools,
                    convert_nums=convert_nums,
                    indent=indent,
                    level=level+1,
                    prevtype='array')

                # Last item of the loop
                if data[-1] == val:
                    rv += "\n%s]" % (indent * (level-1))
                else:
                    rv += ",\n"

    return rv


def encode_nginx(
        data, block_semicolon=False, indent="  ", level=0, semicolon=';',
        semicolon_ignore_postfix='!;'):
    """Convert Python data structure to Nginx format."""

    # Return value
    rv = ""
    # Indicates the item type [section|line]
    item_type = ""

    for item in data:
        if isinstance(item, dict):
            # Section
            if item_type in ('section', 'line'):
                rv += "\n"

            rv += "%s%s {\n" % (level*indent, list(item.keys())[0])
            rv += encode_nginx(
                list(item.values())[0],
                level=level+1,
                block_semicolon=block_semicolon,
                semicolon=semicolon,
                semicolon_ignore_postfix=semicolon_ignore_postfix)
            rv += "%s}%s\n" % (
                level*indent, semicolon if block_semicolon else '')

            item_type = 'section'

        elif isinstance(item, string_types):
            # Normal line
            if item_type == 'section':
                rv += "\n"

            item_type = 'line'
            ignore_semicolon = False

            if item.endswith(semicolon_ignore_postfix):
                item = item[:-len(semicolon_ignore_postfix)]
                ignore_semicolon = True

            rv += "%s%s" % (level*indent, item)

            # Do not finish comments with semicolon
            if item.startswith("# ") or ignore_semicolon:
                rv += "\n"
            else:
                rv += "%s\n" % (semicolon)

        else:
            raise errors.AnsibleFilterError(
                "Unexpected data type: %s" % (type(item)))

    return rv


def encode_pam(
        data, print_label=False, separate_types=True, separator="  "):
    """Convert Python data structure to PAM format."""

    # Return value
    rv = ""
    # Remember previous type to make newline between type blocks
    prev_type = None

    for label, rule in sorted(data.items()):
        if separate_types:
            # Add extra newline to separate blocks of the same type
            if prev_type is not None and prev_type != rule['type']:
                rv += "\n"

            prev_type = rule['type']

        if print_label:
            rv += "# %s\n" % label

        if 'service' in rule:
            rv += "%s%s" % (rule['service'], separator)

        if 'silent' in rule and rule['silent']:
            rv += '-'

        rv += "%s%s" % (rule['type'], separator)

        if isinstance(rule['control'], list):
            rv += "[%s]%s" % (
                " ".join(
                    map(
                        lambda k: "=".join(map(str, k)),
                        map(lambda x: list(x.items())[0], rule['control']))),
                separator)
        else:
            rv += "%s%s" % (rule['control'], separator)

        rv += rule['path']

        if 'args' in rule and rule['args']:
            rv += separator

            for i, arg in enumerate(rule['args']):
                if i > 0:
                    rv += ' '

                if isinstance(arg, dict):
                    rv += "=".join(map(str, list(arg.items())[0]))
                else:
                    rv += arg

        rv += "\n"

    return rv


def encode_toml(
        data, convert_bools=False, convert_nums=False, first=True, quote='"',
        table_name="", table_type=None):
    """Convert Python data structure to TOML format."""

    # Return value
    rv = ""

    if isinstance(data, dict):
        # It's a dict

        tn = table_name

        # First process all keys with elementar value (num/str/bool/array)
        for k, v in sorted(data.items()):

            if not (isinstance(v, dict) or isinstance(v, list)):
                if tn:
                    if not first:
                        rv += "\n"

                    if table_type == 'table':
                        rv += "[%s]\n" % tn
                    else:
                        rv += "[[%s]]\n" % tn

                rv += "%s = %s\n" % (
                    k,
                    encode_toml(
                        v,
                        convert_bools=convert_bools,
                        convert_nums=convert_nums,
                        first=first,
                        quote=quote))

                first = False
                tn = ''
            elif isinstance(v, list) and (not v or not isinstance(v[0], dict)):
                if tn:
                    if not first:
                        rv += "\n"

                    if table_type == 'table':
                        rv += "[%s]\n" % tn
                    else:
                        rv += "[[%s]]\n" % tn

                rv += "%s = %s\n" % (
                    k,
                    encode_toml(
                        v,
                        convert_bools=convert_bools,
                        convert_nums=convert_nums,
                        first=first,
                        quote=quote))

                first = False
                tn = ''

        if not data and table_type is not None:
            if not first:
                rv += "\n"

            if table_type == 'table':
                rv += "[%s]\n" % tn
            else:
                rv += "[[%s]]\n" % tn

        # Then process tables and arrays of tables
        for k, v in sorted(data.items()):
            tn = table_name

            if isinstance(v, dict):
                # Table
                tk = k

                if '.' in k:
                    tk = "%s%s%s" % (quote, _escape(k, quote), quote)

                if tn:
                    tn += ".%s" % tk
                else:
                    tn += "%s" % tk

                rv += encode_toml(
                    v,
                    convert_bools=convert_bools,
                    convert_nums=convert_nums,
                    first=first,
                    quote=quote,
                    table_name=tn,
                    table_type='table')

                first = False
            elif isinstance(v, list) and (not v or isinstance(v[0], dict)):
                # Array of tables
                tk = k

                if '.' in k:
                    tk = "%s%s%s" % (quote, _escape(k, quote), quote)

                if tn:
                    tn += ".%s" % tk
                else:
                    tn += "%s" % tk

                for t in v:
                    rv += encode_toml(
                        t,
                        convert_bools=convert_bools,
                        convert_nums=convert_nums,
                        first=first,
                        quote=quote,
                        table_name=tn,
                        table_type='table_array')

                    first = False

    elif isinstance(data, list):

        # Check if all values are elementar (num/str/bool/array)
        def is_elem(a):
            all_elementar = True

            for lv in a:
                if (
                        isinstance(lv, dict) or (
                            isinstance(lv, list) and
                            not is_elem(lv))):
                    all_elementar = False
                    break

            return all_elementar

        if is_elem(data):
            v_len = len(data)

            array = ''

            for i, lv in enumerate(data):
                array += "%s" % encode_toml(
                    lv,
                    convert_bools=convert_bools,
                    convert_nums=convert_nums,
                    first=first,
                    quote=quote)

                if i+1 < v_len:
                    array += ', '

            rv += "[%s]" % (array)

    elif (
            _is_num(data) or
            isinstance(data, bool) or
            (convert_nums and _str_is_num(data)) or
            (convert_bools and _str_is_bool(data))):
        # It's number or boolean

        rv += str(data).lower()

    elif isinstance(data, string_types):
        # It's a string

        rv += "%s%s%s" % (quote, _escape(data, quote), quote)

    return rv


def encode_xml(
        data, attribute_sign="^", escape_xml=True, indent="  ", level=0):
    """Convert Python data structure to XML format."""

    # Return value
    rv = ""

    if isinstance(data, list):
        # Pocess anything what's not attribute
        for item in data:
            if (
                    not (
                        isinstance(item, dict) and
                        list(item.keys())[0].startswith(attribute_sign))):
                rv += encode_xml(
                    item,
                    attribute_sign=attribute_sign,
                    indent=indent,
                    level=level,
                    escape_xml=escape_xml)
    elif isinstance(data, dict):
        # It's eiher an attribute or an element

        key, val = list(data.items())[0]

        if key.startswith(attribute_sign):
            # Process attribute
            rv += ' %s="%s"' % (key[1:], _escape(val))
        else:
            # Process element
            rv = '%s<%s' % (level*indent, key)

            # Check if there are any attributes
            if isinstance(val, list):
                num_attrs = 0

                for item in val:
                    if (
                            isinstance(item, dict) and
                            list(item.keys())[0].startswith(attribute_sign)):
                        num_attrs += 1
                        rv += encode_xml(
                            item,
                            attribute_sign=attribute_sign,
                            indent=indent,
                            level=level)

            if val == '' or (isinstance(val, list) and num_attrs == len(val)):
                # Close the element as empty
                rv += " />\n"
            else:
                # Close the element as normal
                rv += ">"

                # Check if the value is text
                val_not_text = False

                if isinstance(val, list):
                    # Check if it contains only attributes and a text value
                    for item in val:
                        if (isinstance(item, dict) and not list(
                                item.keys())[0].startswith(attribute_sign)):
                            val_not_text = True
                            break
                elif isinstance(val, dict):
                    val_not_text = True

                if val_not_text:
                    rv += "\n"

                # Process inner content of the element
                rv += encode_xml(
                    val,
                    attribute_sign=attribute_sign,
                    indent=indent,
                    level=level+1,
                    escape_xml=escape_xml)

                if val_not_text:
                    rv += level*indent

                rv += "</%s>\n" % key
    else:
        # It's a string

        rv += "%s" % _escape(data, format=('xml' if escape_xml else None))

    return rv


def encode_yaml(
        data, block_prefix=';;;', convert_bools=False, convert_nums=False,
        indent="  ", level=0, quote='"', skip_indent=False):
    """Convert Python data structure to YAML format."""

    # Return value
    rv = ""

    if isinstance(data, dict):
        # It's a dictionary

        if len(data.keys()) == 0:
            rv += "{}\n"
        else:
            for i, (key, val) in enumerate(sorted(data.items())):
                # Skip indentation only for the first pair
                rv += "%s%s:" % (
                    "" if i == 0 and skip_indent else level*indent, key)

                if isinstance(val, dict) and len(val.keys()) == 0:
                    rv += " {}\n"
                else:
                    if (
                            isinstance(val, dict) or (
                                isinstance(val, list) and
                                len(val) != 0)):
                        rv += "\n"
                    else:
                        rv += " "

                    rv += encode_yaml(
                        val,
                        block_prefix=block_prefix,
                        convert_bools=convert_bools,
                        convert_nums=convert_nums,
                        indent=indent,
                        level=level+1,
                        quote=quote)

    elif isinstance(data, list):
        # It's a list

        if len(data) == 0:
            rv += "[]\n"
        else:
            for item in data:
                if isinstance(item, list):
                    list_indent = "%s-\n" % (level*indent)
                else:
                    list_indent = "%s- " % (level*indent)

                rv += "%s%s" % (list_indent, encode_yaml(
                    item,
                    block_prefix=block_prefix,
                    convert_bools=convert_bools,
                    convert_nums=convert_nums,
                    indent=indent,
                    level=level+1,
                    quote=quote,
                    skip_indent=True))

    elif (
            data == "null" or
            isinstance(data, bool) or
            (convert_bools and _str_is_bool(data))):
        # It's a boolean

        rv += "%s\n" % str(data).lower()

    elif (
            _is_num(data) or
            (convert_nums and _str_is_num(data))):
        # It's a number

        rv += "%s\n" % str(data)

    else:
        # It's a string

        if data is None:
            rv += "null\n"
        elif data.startswith(block_prefix):
            rv += "%s\n" % data[len(block_prefix):].replace(
                "\n", "\n%s" % (level*indent))
        else:
            rv += "%s%s%s\n" % (quote, _escape(data, quote), quote)

    return rv


def __eval_replace(match):
    """Evaluate the real value of the variable specified as a string."""

    ret = '__item'
    ret += ''.join(match.groups()[1:])

    # Try to evaluate the value of the special string
    try:
        ret = eval(ret)
    except Exception:
        # Return empty string if something went wrong
        ret = ''

    return str(ret)


def template_replace(data, replacement):
    """Replace special template decorated variable with its real value."""

    # Make the replacement variable visible for the __eval_replace function
    global __item
    __item = replacement

    # Clone the data to keep the original untouched
    local_data = copy(data)

    # Walk through the data structure and try to replace all special strings
    if isinstance(local_data, list):
        local_data = map(
            lambda x: template_replace(x, replacement), local_data)
    elif isinstance(local_data, dict):
        for key, val in local_data.items():
            local_data[key] = template_replace(val, replacement)
    elif isinstance(local_data, string_types):
        # Replace the special string by it's evaluated value
        p = re.compile(r'\{\[\{\s*(\w+)([^}\s]+|)\s*\}\]\}')
        local_data = p.sub(__eval_replace, local_data)

    return local_data


class FilterModule(object):
    """Ansible encoder Jinja2 filters."""

    def filters(self):
        """Expose filters to ansible."""

        return {
            'encode_apache': encode_apache,
            'encode_erlang': encode_erlang,
            'encode_haproxy': encode_haproxy,
            'encode_ini': encode_ini,
            'encode_json': encode_json,
            'encode_logstash': encode_logstash,
            'encode_nginx': encode_nginx,
            'encode_pam': encode_pam,
            'encode_toml': encode_toml,
            'encode_xml': encode_xml,
            'encode_yaml': encode_yaml,
            'template_replace': template_replace,
        }
