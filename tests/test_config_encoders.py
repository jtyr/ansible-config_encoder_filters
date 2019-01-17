import filter_plugins.config_encoders as CE
import os
import unittest
import yaml


class MyTestCase(unittest.TestCase):
    def _load_file(self, kind, encoder, test):
        dir_path = os.path.dirname(os.path.realpath(__file__))

        f = open('%s/files/%s_%s.%s' % (dir_path, encoder, test, kind), 'r')

        if kind == 'in':
            ret = yaml.load(f)
        else:
            ret = f.read()

        f.close()

        return ret

    def _load_input(self, test):
        return self._load_file('in', self._encoder, test)

    def _load_output(self, test):
        return self._load_file('out', self._encoder, test)

    def _test(self, test, **params):
        test_in = test
        test_out = test

        if isinstance(test, list):
            test_in = test[0]
            test_out = test[1]

        my_in = self._load_input(test_in)
        my_out = self._load_output(test_out)

        encoder = getattr(CE, self._encoder)

        self.assertEqual(encoder(my_in, **params), my_out)


class TestApache(MyTestCase):
    _encoder = 'encode_apache'

    def test_boolean(self):
        self._test('boolean')

    def test_boolean_convert(self):
        self._test(['boolean', 'boolean_convert'], convert_bools=True)

    def test_number(self):
        self._test('number')

    def test_number_convert(self):
        self._test(['number', 'number_convert'], convert_nums=True)

    def test_number_quote(self):
        self._test(['number', 'number_quote'], quote_all_nums=True)

    def test_string(self):
        self._test('string')

    def test_string_quote(self):
        self._test(['string', 'string_quote'], quote_all_strings=True)

    def test_vhost(self):
        self._test('vhost')


class TestErlang(MyTestCase):
    _encoder = 'encode_erlang'

    def test_atom(self):
        self._test('atom')

    def test_boolean(self):
        self._test('boolean')

    def test_boolean_convert(self):
        self._test(['boolean', 'boolean_convert'], convert_bools=True)

    def test_number(self):
        self._test('number')

    def test_number_convert(self):
        self._test(['number', 'number_convert'], convert_nums=True)

    def test_string(self):
        self._test('string')

    def test_mixed(self):
        self._test('mixed')


class TestIni(MyTestCase):
    _encoder = 'encode_ini'

    def test_general(self):
        self._test('general')

    def test_section(self):
        self._test('section')

    def test_mixed(self):
        self._test('mixed')

    def test_mixed_comment(self):
        self._test(['mixed', 'mixed_comment'], section_is_comment=True)

    def test_mixed_delimiter(self):
        self._test(['mixed', 'mixed_delimiter'], delimiter=" = ")

    def test_mixed_indent(self):
        self._test(['mixed', 'mixed_indent'], indent="\t")

    def test_mixed_quote(self):
        self._test(['mixed', 'mixed_quote'], quote='"')

    def test_mixed_ucase(self):
        self._test(['mixed', 'mixed_ucase'], ucase_prop=True)


class TestJson(MyTestCase):
    _encoder = 'encode_json'

    def test_boolean(self):
        self._test('boolean')

    def test_boolean_convert(self):
        self._test(['boolean', 'boolean_convert'], convert_bools=True)

    def test_string(self):
        self._test('string')

    def test_number(self):
        self._test('number')

    def test_number_convert(self):
        self._test(['number', 'number_convert'], convert_nums=True)

    def test_list(self):
        self._test('list')

    def test_list_indent(self):
        self._test(['list', 'list_indent'], indent="    ")

    def test_dict(self):
        self._test('dict')


class TestToml(MyTestCase):
    _encoder = 'encode_toml'

    def test_boolean(self):
        self._test('boolean')

    def test_boolean_convert(self):
        self._test(['boolean', 'boolean_convert'], convert_bools=True)

    def test_string(self):
        self._test('string')

    def test_string_quote(self):
        self._test(['string', 'string_quote'], quote="'")

    def test_number(self):
        self._test('number')

    def test_number_convert(self):
        self._test(['number', 'number_convert'], convert_nums=True)

    def test_array(self):
        self._test('array')

    def test_table(self):
        self._test('table')

    def test_table_array(self):
        self._test('table_array')

    def test_table_grafana(self):
        self._test('table_grafana')


class TestXml(MyTestCase):
    _encoder = 'encode_xml'

    def test_element(self):
        self._test('element')

    def test_attribute(self):
        self._test('attribute')


class TestYaml(MyTestCase):
    _encoder = 'encode_yaml'

    def test_boolean(self):
        self._test('boolean')

    def test_boolean_convert(self):
        self._test(['boolean', 'boolean_convert'], convert_bools=True)

    def test_string(self):
        self._test('string')

    def test_string_quote(self):
        self._test(['string', 'string_quote'], quote='')

    def test_number(self):
        self._test('number')

    def test_number_convert(self):
        self._test(['number', 'number_convert'], convert_nums=True)

    def test_list(self):
        self._test('list')

    def test_list_indent(self):
        self._test(['list', 'list_indent'], indent="    ")

    def test_dict(self):
        self._test('dict')

    def test_block(self):
        self._test('block')

    def test_null(self):
        self._test('null')


if __name__ == '__main__':
    unittest.main()
