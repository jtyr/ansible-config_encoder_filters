import filter_plugins.config_encoders as CE
import os
import unittest
import yaml


class MyTestCase(unittest.TestCase):
    def _load_file(self, kind, plugin, test):
        dir_path = os.path.dirname(os.path.realpath(__file__))

        f = open('%s/files/%s_%s.%s' % (dir_path, plugin, test, kind), 'r')

        if kind == 'in':
            ret = yaml.load(f)
        else:
            ret = f.read()

        f.close()

        return ret

    def _load_input(self, test):
        return self._load_file('in', self._plugin, test)

    def _load_output(self, test):
        return self._load_file('out', self._plugin, test)

    def _test(self, test, **params):
        test_in = test
        test_out = test

        if isinstance(test, list):
            test_in = test[0]
            test_out = test[1]

        my_in = self._load_input(test_in)
        my_out = self._load_output(test_out)

        self.assertEqual(CE.encode_yaml(my_in, **params), my_out)


class TestYaml(MyTestCase):
    _plugin = 'encode_yaml'

    def test_boolean(self):
        self._test('boolean')
        self._test(['boolean', 'boolean_convert'], convert_bools=True)

    def test_string(self):
        self._test('string')
        #self._test(['string', 'string_quote'], quote='')

    def test_number(self):
        self._test('number')
        self._test(['number', 'number_convert'], convert_nums=True)

    def test_list(self):
        self._test('list')
        self._test(['list', 'list_indent'], indent="    ")

    def test_dict(self):
        self._test('dict')


if __name__ == '__main__':
    unittest.main()
