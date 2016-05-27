"""
The latest version of this package is available at:
<http://github.com/jantman/RPyMostat-sensor>

##################################################################################
Copyright 2016 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

    This file is part of RPyMostat-sensor, also known as RPyMostat-sensor.

    RPyMostat-sensor is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    RPyMostat-sensor is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with RPyMostat-sensor.  If not, see <http://www.gnu.org/licenses/>.

The Copyright and Authors attributions contained herein may not be removed or
otherwise altered, except to add the Author attribution of a contributor to
this work. (Additional Terms pursuant to Section 7b of the AGPL v3)
##################################################################################
While not legally required, I sincerely request that anyone who finds
bugs please submit them at <https://github.com/jantman/RPyMostat-sensor> or
to me via email, and that you send any contributions or improvements
either as a pull request on GitHub, or to me via email.
##################################################################################

AUTHORS:
Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>
##################################################################################
"""

import sys
import pytest
import pkg_resources

from rpymostat_sensor.sensor_daemon import SensorDaemon
from rpymostat_sensor.sensors.dummy import DummySensor

# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import patch, call, Mock, DEFAULT  # noqa
else:
    from unittest.mock import patch, call, Mock, DEFAULT  # noqa

pbm = 'rpymostat_sensor.sensor_daemon'
pb = '%s.SensorDaemon' % pbm


class TestSensorDaemon(object):

    def setup(self):
        with patch.multiple(
            pb,
            autospec=True,
            find_host_id=DEFAULT,
            discover_engine=DEFAULT,
            discover_sensors=DEFAULT,
        ) as mocks:
            mocks['find_host_id'].return_value = 'myhostid'
            mocks['discover_engine'].return_value = ('foo.bar.baz', 1234)
            mocks['discover_sensors'].return_value = {
                'sensor1': {'foo': 'bar'}
            }
            self.cls = SensorDaemon()

    def test_init_default(self):
        sensors = [Mock(), Mock()]
        with patch('%s.logger' % pbm, autospec=True) as mock_logger:
            with patch.multiple(
                pb,
                autospec=True,
                find_host_id=DEFAULT,
                discover_engine=DEFAULT,
                discover_sensors=DEFAULT,
            ) as mocks:
                mocks['find_host_id'].return_value = 'myhostid'
                mocks['discover_engine'].return_value = ('foo.bar.baz', 1234)
                mocks['discover_sensors'].return_value = sensors
                cls = SensorDaemon()
        assert cls.dry_run is False
        assert cls.dummy_data is False
        assert cls.engine_port == 1234
        assert cls.engine_addr == 'foo.bar.baz'
        assert cls.interval == 60.0
        assert cls.host_id == 'myhostid'
        assert cls.sensors == sensors
        assert mock_logger.mock_calls == [
            call.warning('This machine running with host_id %s', 'myhostid')
        ]
        assert mocks['find_host_id'].mock_calls == [call(cls)]
        assert mocks['discover_engine'].mock_calls == [call(cls)]
        assert mocks['discover_sensors'].mock_calls == [call(cls, {})]

    def test_init_nondefault(self):
        dummy = Mock()
        with patch('%s.logger' % pbm, autospec=True) as mock_logger:
            with patch.multiple(
                pb,
                autospec=True,
                find_host_id=DEFAULT,
                discover_engine=DEFAULT,
                discover_sensors=DEFAULT,
            ) as mocks:
                mocks['find_host_id'].return_value = 'myhostid'
                mocks['discover_engine'].return_value = ('foo.bar.baz', 1234)
                mocks['discover_sensors'].return_value = [dummy]
                cls = SensorDaemon(
                    dry_run=True,
                    dummy_data=True,
                    engine_port=1234,
                    engine_addr='foo.bar.baz',
                    interval=12.34,
                    class_args={'foo': 'bar'}
                )
        assert cls.dry_run is True
        assert cls.dummy_data is True
        assert cls.engine_port == 1234
        assert cls.engine_addr == 'foo.bar.baz'
        assert cls.interval == 12.34
        assert cls.host_id == 'myhostid'
        assert cls.sensors == [dummy]
        assert mock_logger.mock_calls == [
            call.warning('This machine running with host_id %s', 'myhostid'),
            call.warning("DRY RUN MODE - will not POST data to Engine.")
        ]
        assert mocks['find_host_id'].mock_calls == [call(cls)]
        assert mocks['discover_engine'].mock_calls == []
        assert mocks['discover_sensors'].mock_calls == [
            call(cls, {'foo': 'bar'})
        ]

    def test_init_no_sensors(self):
        with patch('%s.logger' % pbm, autospec=True) as mock_logger:
            with patch.multiple(
                pb,
                autospec=True,
                find_host_id=DEFAULT,
                discover_engine=DEFAULT,
                discover_sensors=DEFAULT,
            ) as mocks:
                mocks['find_host_id'].return_value = 'myhostid'
                mocks['discover_engine'].return_value = ('foo.bar.baz', 1234)
                with pytest.raises(SystemExit) as excinfo:
                    SensorDaemon()
        assert mock_logger.mock_calls == [
            call.warning('This machine running with host_id %s', 'myhostid'),
            call.critical('ERROR - no sensors discovered.')
        ]
        assert mocks['find_host_id'].call_count == 1
        assert mocks['discover_engine'].call_count == 1
        assert mocks['discover_sensors'].call_count == 1
        assert excinfo.value.code == 1

    def test_run(self):
        def se_ras(klass):
            if mock_ras.call_count < 4:
                return None
            raise RuntimeError()

        with patch('%s.read_and_send' % pb, autospec=True) as mock_ras:
            with patch('%s.sleep' % pbm, autospec=True) as mock_sleep:
                with patch('%s.logger' % pbm, autospec=True) as mock_logger:
                    mock_ras.side_effect = se_ras
                    with pytest.raises(RuntimeError):
                        self.cls.run()
        assert mock_ras.mock_calls == [
            call(self.cls),
            call(self.cls),
            call(self.cls),
            call(self.cls)
        ]
        assert mock_sleep.mock_calls == [
            call(60.0),
            call(60.0),
            call(60.0)
        ]
        assert mock_logger.mock_calls == [
            call.info('Running sensor daemon loop...'),
            call.debug('Sleeping %ss', 60.0),
            call.debug('Sleeping %ss', 60.0),
            call.debug('Sleeping %ss', 60.0)
        ]

    def test_sensor_classes(self):

        class EP1(object):
            name = 'EP1'

        mock_ep1 = Mock(spec_set=pkg_resources.EntryPoint)
        type(mock_ep1).name = 'ep1'
        mock_ep1.load.return_value = EP1

        class EP2(object):
            name = 'EP2'

        mock_ep2 = Mock(spec_set=pkg_resources.EntryPoint)
        type(mock_ep2).name = 'ep1'
        mock_ep2.load.return_value = EP2

        class EP3(object):
            name = 'EP3'

        mock_ep3 = Mock(spec_set=pkg_resources.EntryPoint)
        type(mock_ep3).name = 'ep3'
        mock_ep3.load.return_value = EP3

        entry_points = [mock_ep1, mock_ep2, mock_ep3]

        with patch('%s.DummySensor' % pbm, autospec=True) as mock_dummy:
            with patch('%s.logger' % pbm, autospec=True) as mock_logger:
                with patch('%s.pkg_resources.iter_entry_points' % pbm,
                           autospec=True) as mock_iep:
                    mock_iep.return_value = entry_points
                    res = self.cls._sensor_classes()
        assert res == [EP1, EP2, EP3]
        assert mock_dummy.mock_calls == []
        assert mock_iep.mock_calls == [call('rpymostat.sensors')]
        assert mock_logger.mock_calls == [
            call.debug('Loading sensor classes from entry points.'),
            call.debug('Trying to load sensor class from entry point: %s',
                       'ep1'),
            call.debug('Trying to load sensor class from entry point: %s',
                       'ep1'),
            call.debug('Trying to load sensor class from entry point: %s',
                       'ep3'),
            call.debug("%s Sensor classes loaded successfully: %s",
                       3, ['EP1', 'EP2', 'EP3'])
        ]

    def test_discover_sensors(self):

        class Class1(object):

            def sensors_present(self):
                pass

        class Class2(object):

            def sensors_present(self):
                pass

        class Class3(object):

            def sensors_present(self):
                pass

        class Class4(object):

            def sensors_present(self):
                pass

        def se_exc(s):
            raise RuntimeError()

        mock_cls1 = Mock(spec=Class1)
        mock_cls1.sensors_present.return_value = True
        mock1 = Mock(spec=Class1)
        mock1.return_value = mock_cls1

        mock_cls2 = Mock(spec=Class2)
        mock_cls2.sensors_present.return_value = False
        mock2 = Mock(spec=Class2)
        mock2.return_value = mock_cls2

        mock_cls3 = Mock(spec=Class3)
        mock_cls3.sensors_present.side_effect = se_exc
        mock3 = Mock(spec=Class3)
        mock3.return_value = mock_cls3

        mock4 = Mock(spec=Class4)
        mock4.side_effect = se_exc

        classes = [mock1, mock2, mock3, mock4]

        cls_args = {'Class1': {'foo': 'bar'}}

        with patch('%s.logger' % pbm, autospec=True) as mock_logger:
            with patch('%s._sensor_classes' % pb, autospec=True) as m_classes:
                m_classes.return_value = classes
                res = self.cls.discover_sensors(class_args=cls_args)
        assert res == [mock_cls1]
        assert m_classes.mock_calls == [call(self.cls)]
        assert mock_cls1.mock_calls == [call.sensors_present()]
        assert mock1.mock_calls == [
            call(foo='bar'),
            call().sensors_present()
        ]
        assert mock_logger.mock_calls == [
            call.debug('Checking sensor classes for sensors...'),
            call.info('Sensor class %s.%s reports sensors present',
                      'rpymostat_sensor.tests.test_sensor_daemon', 'Class1'),
            call.debug('Exception while discovering sensors via %s.%s',
                       'rpymostat_sensor.tests.test_sensor_daemon',
                       'Class3', exc_info=1),
            call.debug('Exception while instantiating sensor class %s with '
                       'kwargs=%s', 'Class4', {}, exc_info=1),
            call.debug('Discovered %d sensor classes with sensors present', 1)
        ]

    def test_dummy_sensor(self):
        res = self.cls.dummy_sensor()
        assert len(res) == 1
        assert isinstance(res[0], DummySensor)

    def test_read_and_send(self):
        pass
