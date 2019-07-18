import os
import sys
import logging
import shutil
if sys.version_info[0] == 2:
    import ConfigParser as configparser
else:
    import configparser
default_project = 'CiS2.0'
logger = logging.getLogger('CiS2.0')


# Create user config file
this_dir = os.path.dirname(__file__)
def_config_file = os.path.join(this_dir, 'project.cfg')
usr_config_file = os.path.expanduser(os.path.join(
    '~', '.%s_management.cfg' % default_project))
if not os.path.isfile(usr_config_file):
    shutil.copy(def_config_file, usr_config_file)
    logger.info(("Created user config file here: %s\n"
                 "Any modifications (e.g. your tokens should go in that file "
                 "and not the default config file located here: %s")
                % (usr_config_file, def_config_file))


# Load config and set options
config = configparser.ConfigParser(
    interpolation=configparser.ExtendedInterpolation())
config.read([def_config_file, usr_config_file])
if not os.path.isabs(config['general']['contacts_file']):
    config['general']['contacts_file'] = os.path.join(
        this_dir, config['general']['contacts_file'])
config['github']['cache_file'] = os.path.join(
    config['github']['cache_dir'],
    config['github']['cache_file_format'])
config['smartsheet']['cache_file'] = os.path.join(
    config['smartsheet']['cache_dir'],
    config['smartsheet']['cache_file_format'])
