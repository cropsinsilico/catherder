import logging
import argparse
from catherder import classes, config
logFormatter = logging.Formatter("[%(levelname)-8s] %(message)s")
logger = logging.getLogger('catherder')
logger.setLevel(logging.INFO)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)


def call_catherder():
    r"""Call catherder."""
    parser = argparse.ArgumentParser(
        "Update the cache's of project data on Github/Smartsheet.")
    parser.add_argument('--configure', action='store_true',
                        help='Run configuration for the specified projects.')
    parser.add_argument('project', nargs='*',
                        help='The names of one or more projects to sync.')
    parser.add_argument('--sort-project-cards', action='store_true',
                        help='Sort the project cards after other actions.')
    parser.add_argument('--smartsheet', action='store_true',
                        help='Update Smartsheet from Github.')
    parser.add_argument('--github', action='store_true',
                        help='Update Github from Smartsheet.')
    parser.add_argument('--assignees', action='store_true',
                        help=('Update assignees on Github without moving the '
                              'cards.'))
    parser.add_argument('--dont-suspend-automation', action='store_true',
                        help=('Don\'t suspend automation of project card '
                              'movement across columns during update.'))
    parser.add_argument('--yes', '-y', action='store_true',
                        help=('Automatically answer yes to all questions '
                              'about updates.'))
    args = parser.parse_args()
    if not args.project:
        if config.default_config.has_option('general', 'default_project'):
            args.project.append(
                config.default_config['general']['default_project'])
        else:
            config.initial_config()
    for project in args.project:
        if args.configure:
            config.read_project_config(project)
        x_sm = classes.SmartsheetAPI(project_name=project, always_yes=args.yes)
        x_gh = classes.GithubAPI(project_name=project, always_yes=args.yes)
        if args.smartsheet:
            logger.info("Updating Smartsheet from Github")
            x_sm.update_remote(x_gh)
        if args.github:
            logger.info("Updating Github from Smartsheet")
            x_gh.update_remote(
                x_sm, suspend_progress_automation=(
                    not args.dont_suspend_automation))
        if args.assignees:
            logger.info("Updating Github assignees.")
            x_gh.update_remote(x_sm)
            # Don't update card column to in progress due to editting assignees
            x_gh.update_remote(x_sm, update_assignees=True,
                               suspend_progress_automation=True)
        if args.sort_project_cards:
            logger.info("Sorting Github project cards")
            x_gh.sort_cards()


if __name__ == '__main__':
    call_catherder()
