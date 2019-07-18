import logging
import argparse
from catherder import classes
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
    parser.add_argument('--suspend-automation', action='store_true',
                        help=('Suspend automation of project card movement '
                              'across columns.'))
    args = parser.parse_args()
    if not args.project:
        args.project.append(None)
    for project in args.project:
        x_sm = classes.SmartsheetAPI(project_name=project)
        x_gh = classes.GithubAPI(project_name=project)
        if args.smartsheet:
            logger.info("Updating Smartsheet from Github")
            x_sm.update_remote(x_gh)
        if args.github:
            logger.info("Updating Github from Smartsheet")
            x_gh.update_remote(
                x_sm, suspend_progress_automation=args.suspend_automation)
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
