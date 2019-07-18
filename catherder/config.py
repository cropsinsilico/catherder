import os
import sys
import logging
import shutil
if sys.version_info[0] == 2:
    import ConfigParser as configparser
else:
    import configparser
logger = logging.getLogger(__name__)


# Create user config file
this_dir = os.path.dirname(__file__)
def_config_file = os.path.join(this_dir, 'default_project.cfg')
usr_config_file = os.path.expanduser(os.path.join('~', '.catherder.cfg'))
usr_config_file_old = os.path.expanduser(os.path.join(
    '~', '.CiS2.0_management.cfg'))
if not os.path.isfile(usr_config_file):
    if os.path.isfile(usr_config_file_old):  # pragma: no cover
        # This specifically handles backwards compatibility with the previous
        # iteration which was catered to a specific project
        logger.info(("Config file exists at old location (%s). This file will "
                     "be moved to %s.") % (usr_config_file_old,
                                           usr_config_file))
        shutil.move(usr_config_file_old, usr_config_file)
        config = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation())
        config.read(usr_config_file)
        config['general']['default_project'] = 'CiS2.0'
        config.add_section('CiS2.0')
        config['CiS2.0']['github_repository'] = config['github']['repository']
        config['CiS2.0']['github_project'] = config['github']['project']
        config['CiS2.0']['smartsheet_sheet'] = config['smartsheet']['sheet']
        config.remove_option('github', 'repository')
        config.remove_option('github', 'project')
        config.remove_option('smartsheet', 'sheet')
        with open(usr_config_file, 'w') as fd:
            config.write(fd)
    else:
        shutil.copy(def_config_file, usr_config_file)
        logger.info(("Created user config file here: %s\n"
                     "Any modifications (e.g. your tokens should go in that "
                     "file and not the default config file located here: %s")
                    % (usr_config_file, def_config_file))


def read_project_config(project_name=None):
    r"""Read a configuration file for a project. If the file dosn't exist, an
    empty one will be created for the project with the format
    <project_name>.cfg in the pkg_config_dir (~/catherder).

    Args:
        project_name (str, optional): Name of the project. If not provided,
            the 'general' section of the config file will be checked for a
            'default_project' option. If there is not a 'default_project'
            option defined, an error will be raised.

    Returns:
        configparser.ConfigParser: Dictionary like object providing access to
            the read configuration options.

    Raises:
        ValueError: If a project_name is not provided and the 'default_project'
            option is not set in the 'general' section of the config file.

    """
    config = configparser.ConfigParser(
        interpolation=configparser.ExtendedInterpolation())
    config.read([def_config_file, usr_config_file])
    if (project_name is None) and config.has_option('general',
                                                    'default_project'):
        project_name = config['general']['default_project']
    if not project_name:
        raise ValueError(("No project specified and the 'default_project' "
                          "option in the 'general' section of your config "
                          "file is not set."))
    # Create section for a missing project
    if (project_name is not True) and (not config.has_section(project_name)):
        config.add_section(project_name)
        config.add_option(project_name, 'github_repository',
                          input(('Enter the name of the Github repository '
                                 'containing the project '
                                 'and issues that should be synced '
                                 'in the form <user/organization>/<repo>. '
                                 'This repo is also used to cache data on '
                                 'the status of the project.: ')))
        config.add_option(project_name, 'github_project',
                          input(('Enter the name of the Github project that '
                                 'tracks issues in the specified repo.: ')))
        config.add_option(project_name, 'smartsheet_sheet',
                          input(('Enter the name of the Smartsheet sheet that '
                                 'should be synced.: ')))
        with open(usr_config_file, 'w') as fd:
            config.write(fd)
    # Update global results based on project specific settings
    if (project_name is not True):
        config['github']['repository'] = (
            config[project_name]['github_repository'])
        config['github']['project'] = config[project_name]['github_project']
        config['smartsheet']['sheet'] = (
            config[project_name]['smartsheet_sheet'])
        if config.has_option(project_name, 'contacts_file'):
            config['general']['contacts_file'] = (
                config[project_name]['contacts_file'])
        if config.has_option(project_name, 'github_token'):
            config['github']['token'] = config[project_name]['github_token']
        if config.has_option(project_name, 'smartsheet_token'):
            config['smartsheet']['token'] = (
                config[project_name]['smartsheet_token'])
    # Complete paths
    config['github']['cache_file'] = os.path.join(
        config['github']['cache_dir'],
        config['github']['cache_file_format'])
    config['smartsheet']['cache_file'] = os.path.join(
        config['smartsheet']['cache_dir'],
        config['smartsheet']['cache_file_format'])
    return config


default_config = read_project_config(project_name=True)
