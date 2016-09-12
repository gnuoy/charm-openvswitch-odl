# Copyright 2016 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import print_function

import unittest

import mock

import reactive.openvswitch_odl_handlers as handlers


_when_args = {}
_when_not_args = {}


def mock_hook_factory(d):

    def mock_hook(*args, **kwargs):

        def inner(f):
            # remember what we were passed.  Note that we can't actually
            # determine the class we're attached to, as the decorator only gets
            # the function.
            try:
                d[f.__name__].append(dict(args=args, kwargs=kwargs))
            except KeyError:
                d[f.__name__] = [dict(args=args, kwargs=kwargs)]
            return f
        return inner
    return mock_hook


class TestOVSODLHandlers(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._patched_when = mock.patch('charms.reactive.when',
                                       mock_hook_factory(_when_args))
        cls._patched_when_started = cls._patched_when.start()
        cls._patched_when_not = mock.patch('charms.reactive.when_not',
                                           mock_hook_factory(_when_not_args))
        cls._patched_when_not_started = cls._patched_when_not.start()
        # force requires to rerun the mock_hook decorator:
        # try except is Python2/Python3 compatibility as Python3 has moved
        # reload to importlib.
        try:
            reload(handlers)
        except NameError:
            import importlib
            importlib.reload(handlers)

    @classmethod
    def tearDownClass(cls):
        cls._patched_when.stop()
        cls._patched_when_started = None
        cls._patched_when = None
        cls._patched_when_not.stop()
        cls._patched_when_not_started = None
        cls._patched_when_not = None
        # and fix any breakage we did to the module
        try:
            reload(handlers)
        except NameError:
            import importlib
            importlib.reload(handlers)

    def setUp(self):
        self._patches = {}
        self._patches_start = {}

    def tearDown(self):
        for k, v in self._patches.items():
            v.stop()
            setattr(self, k, None)
        self._patches = None
        self._patches_start = None

    def patch(self, obj, attr, return_value=None):
        mocked = mock.patch.object(obj, attr)
        self._patches[attr] = mocked
        started = mocked.start()
        started.return_value = return_value
        self._patches_start[attr] = started
        setattr(self, attr, started)

    def test_registered_hooks(self):
        # test that the hooks actually registered the relation expressions that
        # are meaningful for this interface: this is to handle regressions.
        # The keys are the function names that the hook attaches to.
        when_patterns = {
            'configure_openvswitch': ('charm.installed',
                                      'ovsdb-manager.access.available',),
            'unconfigure_openvswitch': ('ovs.configured', ),
            'configure_neutron_plugin': ('neutron-plugin.connected', ),
            'odl_node_registration': ('controller-api.access.available', ),
            'odl_mac_registration': ('controller-api.access.available', ),
        }
        when_not_patterns = {
            'install_packages': ('charm.installed', ),
            'unconfigure_openvswitch': ('ovsdb-manager.access.available', ),
        }
        # check the when hooks are attached to the expected functions
        for t, p in [(_when_args, when_patterns),
                     (_when_not_args, when_not_patterns)]:
            for f, args in t.items():
                # check that function is in patterns
                self.assertTrue(f in p.keys(),
                                "{} not found".format(f))
                # check that the lists are equal
                l = []
                for a in args:
                    l += a['args'][:]
                self.assertEqual(sorted(l), sorted(p[f]),
                                 "{}: incorrect state registration".format(f))

    def test_install_packages(self):
        self.patch(handlers.ovs_odl, 'install')
        self.patch(handlers.reactive, 'set_state')
        handlers.install_packages()
        self.install.assert_called_once_with()
        self.set_state.assert_called_once_with('charm.installed')

    def test_configure_openvswitch(self):
        odl_ovsdb = mock.MagicMock()
        self.patch(handlers.ovs_odl, 'configure_openvswitch')
        self.patch(handlers.reactive, 'set_state')
        handlers.configure_openvswitch(odl_ovsdb)
        self.configure_openvswitch.assert_called_once_with(odl_ovsdb)
        self.set_state.assert_called_once_with('ovs.configured')

    def test_unconfigure_openvswitch(self):
        odl_ovsdb = mock.MagicMock()
        self.patch(handlers.ovs_odl, 'unconfigure_openvswitch')
        self.patch(handlers.reactive, 'remove_state')
        handlers.unconfigure_openvswitch(odl_ovsdb)
        self.unconfigure_openvswitch.assert_called_once_with(odl_ovsdb)
        self.remove_state.assert_called_once_with('ovs.configured')

    def test_configure_neutron_plugin(self):
        neutron_plugin = mock.MagicMock()
        self.patch(handlers.ovs_odl, 'configure_plugin')
        handlers.configure_neutron_plugin(neutron_plugin)
        self.configure_plugin.assert_called_once_with(neutron_plugin)

    def test_odl_node_registration(self):
        controller = mock.MagicMock()
        self.patch(handlers.ovs_odl, 'register_node')
        handlers.odl_node_registration(controller)
        self.register_node.assert_called_once_with(controller)

    def test_odl_mac_registration(self):
        controller = mock.MagicMock()
        self.patch(handlers.ovs_odl, 'register_macs')
        handlers.odl_mac_registration(controller)
        self.register_macs.assert_called_once_with(controller)
