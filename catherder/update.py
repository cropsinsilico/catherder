import sys
import logging
import classes
logFormatter = logging.Formatter("[%(levelname)-8s] %(message)s")
logger = logging.getLogger('CiS2.0')
logger.setLevel(logging.INFO)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)

x_sm = classes.SmartsheetAPI()
x_gh = classes.GithubAPI()
suspend_progress_automation = ('--suspend-automation' in sys.argv)

if '--sort-project-cards' in sys.argv:
    logger.info("Sorting Github project cards")
    x_gh.sort_cards()
if '--smartsheet' in sys.argv:
    logger.info("Updating Smartsheet from Github")
    x_sm.update_remote(x_gh)
if '--github' in sys.argv:
    logger.info("Updating Github from Smartsheet")
    x_gh.update_remote(x_sm,
                       suspend_progress_automation=suspend_progress_automation)
if '--assignees' in sys.argv:
    logger.info("Updating Github assignees.")
    x_gh.update_remote(x_sm)
    # Don't update card column to in progress due to editting assignees
    x_gh.update_remote(x_sm, update_assignees=True,
                       suspend_progress_automation=True)
