# coding=utf-8
from __future__ import absolute_import

__author__ = "Nils Andresen <Nils@nils-andresen.de>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2023 Nils Andresen - Released under terms of the AGPLv3 License"

import octoprint.plugin
from octoprint.util import RepeatedTimer
import requests

class FHEMTemp(octoprint.plugin.StartupPlugin,
                octoprint.plugin.RestartNeedingPlugin,
                octoprint.plugin.TemplatePlugin,
                octoprint.plugin.SettingsPlugin):

    def __init__(self):
        self.config = dict()
        self.csrf = None
        self._timer = RepeatedTimer(30, self.read_temperatures, run_first=True)
        self._measured = None
        self._desired = None

    def get_settings_defaults(self):
        return dict(
            address = '',
            device_name = '',
            verify_tls = False,
            measured_reading = 'measured-temp',
            desired_reading = 'desired-temp',
            temp_name = 'chamber',
            update_interval = 30
        )


    def on_settings_initialized(self):
        self.config = dict()
        self.reload_settings()
        self.load_csrf()


    def reload_settings(self):
        lastInterval = None
        if('update_interval' in self.config):
            lastInterval = self.config['update_interval']

        # do the update
        for k, v in self.get_settings_defaults().items():
            if type(v) == str:
                v = self._settings.get([k])
            elif type(v) == int:
                v = self._settings.get_int([k])
            elif type(v) == float:
                v = self._settings.get_float([k])
            elif type(v) == bool:
                v = self._settings.get_boolean([k])

            self.config[k] = v
            self._logger.debug("{}: {}".format(k, v))

        # checks
        if (self.config['update_interval'] < 1):
            self._logger.error("Can not set update_interval to anything lower than 1.")
            self.config['update_interval'] = 30

        if (self.config['address'].endswith('/')):
            self._logger.warn("Removing trailing slash from address.")
            self.config['address'] = self.config['address'][:-1]

        # stop and restart timer
        if(lastInterval == None or self.config['update_interval'] != lastInterval):
            self._timer.cancel()
            self._timer = RepeatedTimer(self.config['update_interval'], self.read_temperatures, run_first=False)
            self._timer.start()




    def on_startup(self, host, port):
        self.load_csrf()

    def read_temperatures(self):
        if((not 'address' in self.config) or (not self.config['address'])):
            self._logger.warn('FHEM server not configured.')
            return

        resp = self.send_to_fhem('jsonlist2 {0}'.format(self.config['device_name']))
        list = resp.json()
        if(list is None):
            self._logger.warn('Error getting list data.')
            self._logger.debug(resp.content)
            return

        measuredReading = list['Results'][0]['Readings'][self.config['measured_reading']]['Value']
        if(measuredReading != None):
            self._logger.debug('{0} from readings is: {1}'.format(self.config['measured_reading'], measuredReading))
            self._measured = float(measuredReading)
        else:
            self._measured = None
            self._logger.warn('unable to get a reading from {0}'.format(self.config['measured_reading']))

        if(self.config['desired_reading']):
            desiredReading = list['Results'][0]['Readings'][self.config['desired_reading']]['Value']
            if(desiredReading != None):
                self._logger.debug('{0} from readings is: {1}'.format(self.config['desired_reading'], desiredReading))
                self._desired = float(desiredReading)
            else:
                self._logger.warn('unable to get a reading from {0}'.format(self.config['desired_reading']))
        else:
            self._logger.debug('No setting for `desired_reading` - desired temp is deactivated.')


    def send_to_fhem(self, command, recurse=False):
        url='{0}/fhem'.format(self.config['address'])
        verify_tls=self.config['verify_tls']
        auth=None
        params={
            'cmd':command,
            'XHR':1,
            'fwcsrf': self.csrf
        }
        args={
            'verify': verify_tls,
            'auth': auth,
        }

        self._logger.debug('sending command \'{0}\' to server {1}'.format(command, url))
        resp = requests.get(url, params=params, **args)
        if(resp.status_code == 400 and resp.headers['X-FHEM-csrfToken'] != self.csrf and not recurse):
            # csrf error.
            self._logger.debug('encountered new CSRF')
            self.csrf = resp.headers['X-FHEM-csrfToken']
            return self.send_to_fhem(command, True)

        if(not resp.ok):
            self._logger.error('got status {0} when accessing {1}'.format(resp.status_code, url))

        self.csrf = resp.headers['X-FHEM-csrfToken']
        return resp

    def load_csrf(self):
        if((not 'address' in self.config) or (not self.config['address'])):
            return
        self.send_to_fhem('jsonlist2 {0}'.format(self.config['device_name']))

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.reload_settings()

    def get_settings_version(self):
        return 1

    def on_settings_migrate(self, target, current=None):
        pass

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False)
        ]

    def get_update_information(self):
        return dict(
            fhem_temp=dict(
                displayName="FHEM Temp",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="nils-org",
                repo="OctoPrint-FHEM-Temp",
                current=self._plugin_version,

                # update method: pip w/ dependency links
                pip="https://github.com/nils-org/OctoPrint-FHEM-Temp/archive/{target_version}.zip"
            )
        )

    def add_temperatures(self, comm, parsed_temps):
        if(self._measured != None and self._measured > 0):
            parsed_temps[self.config['temp_name']] = (self._measured, self._desired)

        return parsed_temps

__plugin_name__ = "FHEM Temp"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = FHEMTemp()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.temperatures.received": (__plugin_implementation__.add_temperatures, 1)
    }
