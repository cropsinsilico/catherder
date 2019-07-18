import os
import re
import csv
import copy
import json
import datetime
import shutil
import pprint
import logging
from collections import OrderedDict
import smartsheet
import github
from github import Github, Consts
from catherder import names, utils, config
logger = logging.getLogger(__name__)


_github_issue_format = """\
# {Task Name}

## Summary

#### Assigned PI: {Assigned To}
#### Collaborator(s): {Collaborator}
#### Start Date: {Start}
#### Finish Date: {Finish}

## Tasks

{existing_tasks}

## Management Notes

{Comments}

## Additional Information

{existing_info}

"""


class UpdateAPI(object):

    name = None
    cache_file_format = None
    remote_address_default = None
    dependent_on_remote_data = []

    def __init__(self, project_name=None, remote_address=None, token=None,
                 cache_repo=None):
        self.config = config.read_project_config(project_name=project_name)
        self.names = names.Names(self.config['general']['contacts_file'])
        self.logger = logger
        self.remote_address = remote_address
        self.token = token
        self.cache_repo = cache_repo
        self.local_data = None
        if self.remote_address is None:
            self.remote_address = self.remote_address_default
        if self.token is None:
            self.token = self.config[self.name]['token']
        if not self.token:
            self.token = os.environ.get(
                self.config[self.name]['token_env_var'], None)
        if self.cache_repo is None:
            github_token = self.config['github']['token']
            if not github_token:
                github_token = None
            self.cache_repo = GithubAPI.get_api(github_token).get_repo(
                self.config['github']['repository'])
        self.api = self.get_api(token=self.token)
        self._remote_data = None
        self.update_state()

    @property
    def cache_file_format(self):
        r"""str: Format string that should be used for creating cache file
        names."""
        return self.config[self.name]['cache_file']

    @property
    def remote_data(self):
        r"""object: Remote data API object."""
        if self._remote_data is None:
            self._remote_data = self.load_remote(self.remote_address)
        return self._remote_data

    def return_remote_property(self, prop_name):
        r"""Return property that is dependent on remote."""
        pass

    def on_remote_data_update(self):
        r"""Update dependent properties."""
        for x in self.dependent_on_remote_data:
            setattr(self, '_%s' % x, None)

    @classmethod
    def get_api(cls, token=None):
        r"""Return the top level API object."""
        pass

    @classmethod
    def get_entry(cls, obj_list, key, value, by_attr=False,
                  func_getval=None, func_validate=None, default=False):
        r"""Select an entry from a list by comparing keys/attributes of its
        elements against a value.

        Args:
            obj_list (list): List of objects to compare attributes against.
            key (str): Key/attribute of objects in obj_list that should be
                compared against value for selection.
            value (object): Value that should be compared against.
            by_attr (bool, optional): If True, attributes will be checked. If
                False, dictionary entries will be checked. Defaults to False.
            func_getval (function, optional): Function that takes a list entry
                as input and returns the value. Defaults to getattr or getitem
                depending on by_attr.
            func_validate (function, optional): Function that takes two values
                as input and compares them. Defaults to ==.
            default (object, optional): Entry that should be returned if a
                match cannot be located. Defaults to False and an error will be
                raised if a match cannot be found.

        Returns:
            object: Entry with a matching value.

        Raises:
            ValueError: If a match cannot be located and default is False.

        """
        vals_exist = []
        varname = 'value'
        if func_getval is None:
            if by_attr:
                def func_getval(x):
                    return getattr(x, key)

                varname = 'attribute'
            else:
                def func_getval(x):
                    return x[key]

                varname = 'key'
        if func_validate is None:
            def func_validate(a, b):
                return (a == b)
        for k in obj_list:
            v = func_getval(k)
            if func_validate(v, value):
                return k
            vals_exist.append(v)
        if default is not False:
            return default
        raise ValueError(("Could not locate entry with %s '%s' of '%s'."
                          "Values include: %s")
                         % (varname, key, value, vals_exist))

    def update_remote(self, other, **kwargs):
        r"""Update the remote based on data from an alternate source.

        Args:
            other (object): Data from alternate source that should be used to
                update the remote.
            **kwargs: Additional keyword arguments are passed to
                get_updated_from_other and upload_remote.

        """
        self.update_state()
        old = self.local_data
        new = self.get_updated_from_other(other, **kwargs)
        diff = utils.get_diff(old, new)
        if diff:
            self.logger.info("Diff = \n%s\n" % diff)
            if (input('y/[n]?: ').lower() in ['y', 'yes']):
                if new is not None:
                    self.upload_remote(new, **kwargs)
                self.update_state()
        else:
            self.logger.info("No updates necessary.")

    def get_updated_from_other(self, other, **kwargs):
        r"""Return a version of the local data updated with data from the
        provided alternate data source.

        Args:
            other (UpdateAPI): API instance to update from.
            **kwargs: Additional keyword arguments are passed to the update
                function ('update_from_<other.name>').

        Returns:
            dict: Updated version of self.local_data

        """
        func = getattr(self, 'update_from_%s' % other.name, None)
        if func is None:
            raise NotImplementedError(("Method for updating from %s not "
                                       "implemented.") % other.name)
        prev = copy.deepcopy(self.local_data)
        return func(prev, other, **kwargs)

    def update_state(self, now=None):
        r"""Update the state record in the cache repository.

        Args:
            now (datetime.Datetime, optional): Timestamp that should be used
               in the name for the new file.

        """
        if now is None:
            now = datetime.datetime.utcnow()
        fname_old = utils.find_most_recent(self.cache_file_format,
                                           repo=self.cache_repo)
        fname_new = now.strftime(self.cache_file_format)
        self.download_remote(fname_new)
        if fname_old is None:
            self.commit_state(fname_new,
                              "Creating initial %s cache" % self.name,
                              '%s cache does not exist. Should one be created?'
                              % self.name)
        else:
            diff = utils.get_diff(fname_old, fname_new)
            if diff:
                self.commit_state(fname_new,
                                  "Updating %s cache" % self.name,
                                  ("%s cache is out of date. The diff is "
                                   "\n%s\nShould the cache be updated?")
                                  % (self.name, diff))
            else:
                logger.info("%s cache remains the same." % self.name)
        if os.path.isfile(fname_new) and (self.cache_repo is not None):
            os.remove(fname_new)
        self.local_data = self.load_most_recent()

    def commit_state(self, new_cache, message, question=None):
        r"""Commit the specified file to the cache repository using the
        provided commit message.

        Args:
            new_cache (str): Path to file that should be created. The path
                should be relative to the repository root. The file is
                removed after being committed.

        """
        if question is None:
            question = "Create new cache?"
        print(question)
        if (input('y/[n]?: ').lower() in ['y', 'yes']):
            with open(new_cache, 'rb') as fd:
                self.cache_repo.create_file(new_cache, message, fd.read())
        os.remove(new_cache)

    def load_most_recent(self, default=False):
        r"""Get the remote data for the specified address.

        Args:
            default (object, optional): API object that should be returned if
                the specified address cannot be located.

        Returns:
            object: API object.

        Raises:
            ValueError: If the object cannot be located.

        """
        fd = utils.find_most_recent(self.cache_file_format,
                                    repo=self.cache_repo,
                                    return_tempfile=True)
        try:
            out = self.load_local(fd, default=default)
        finally:
            fd.close()
        return out

    @classmethod
    def load_local(cls, address, default=False):
        r"""Get the local data for the specified address.

        Args:
            address (str): Address for object that should be returned.
            default (object, optional): API object that should be returned if
                the specified address cannot be located.

        Returns:
            object: API object.

        """
        pass

    def load_remote(self, address, default=False):
        r"""Get the remote data for the specified address.

        Args:
            address (str): Address for object that should be returned.
            default (object, optional): API object that should be returned if
                the specified address cannot be located.

        Returns:
            object: API object.

        Raises:
            ValueError: If the object cannot be located.

        """
        pass

    def download_remote(self, address):
        r"""Download remote data to the specified local address.

        Args:
            address (str): Address where object should be saved.

        """
        pass

    def upload_remote(self, data):
        r"""Upload new data to the remote.

        Args:
            data (dict): Data that should be uploaded.

        """
        pass


class GithubAPI(UpdateAPI):
    r"""Class for managing the Github issues.

    Args:
        github_project_name (str, optional): Project where issues are being
            managed. Defaults to self.config['github']['project'].

    """

    name = 'github'

    def __init__(self, *args, **kwargs):
        self._github_project_name = kwargs.pop('github_project_name', None)
        self._github_project = None
        super(GithubAPI, self).__init__(*args, **kwargs)

    @property
    def remote_address_default(self):
        r"""str: The address associated with the remote project data."""
        return self.config['github']['repository']

    @property
    def github_project_name(self):
        r"""str: Name of the Github project."""
        if self._github_project_name is None:
            self._github_project_name = self.config['github']['project']
        return self._github_project_name

    @property
    def github_project(self):
        r"""github.Project.Project: Github project."""
        if self._github_project is None:
            self._github_project = self.get_entry(
                self.remote_data.get_projects(), 'name',
                self.github_project_name, by_attr=True)
        return self._github_project

    @classmethod
    def get_api(cls, token=None):
        r"""Return the top level API object."""
        if token is not None:
            g = Github(token)
        else:
            # Try to read the GITHUB_TOKEN env var
            try:
                g = Github(os.environ["GITHUB_TOKEN"])
            except KeyError:
                logger.error(
                    "Please provide a GitHub auth token using --token "
                    "or the GITHUB_TOKEN env var"
                    )
                raise
        return g

    @classmethod
    def load_local(cls, address, default=False):
        r"""Get the local data for the specified address."""
        if isinstance(address, str):
            assert(os.path.isfile(address))
            with open(address, 'r') as fd:
                out = json.load(fd)
        else:
            out = json.load(address)
        return out

    def load_remote(self, address, default=False):
        r"""Get the remote data for the specified address."""
        return self.api.get_repo(address)

    @classmethod
    def remote2local(cls, remote_data):
        r"""Convert remote version of data to local dictionary.

        Args:
            remote_data (object): Remote data API object.

        Returns:
            dict: Local version of data.

        """
        milestones = []
        for m in remote_data.get_milestones(state='all'):
            milestones.append(cls.remote2local_milestone(m))
        issues = []
        for i in remote_data.get_issues(state='all'):
            issues.append(cls.remote2local_issue(i))
        return {'milestones': milestones, 'issues': issues}

    @classmethod
    def remote2local_milestone(cls, milestone):
        r"""Convert Github milestone object into a dictionary.

        Args:
            milestone (github.Milestone.Milestone): Milestone object to be
                converted.

        Returns:
            dict: Dictionary of data from the Github milestone.

        """
        attr_use = ['title', 'description', 'state', 'due_on']
        out = {k: getattr(milestone, k) for k in attr_use}
        out['due_on'] = out['due_on'].strftime("%m/%d/%y")
        return out

    @classmethod
    def remote2local_issue(cls, issue):
        r"""Convert Github issue object into a dictionary.

        Args:
            issue (github.Issue.Issue): Issue object to be converted.

        Returns:
            dict: Dictionary of data from the Github issue.

        """
        attr_use = ['title', 'body', 'milestone', 'assignees', 'state']
        out = {k: getattr(issue, k) for k in attr_use}
        if out['milestone']:
            out['milestone'] = out['milestone'].title
        if out['assignees']:
            out['assignees'] = [x.login for x in out['assignees']]
        out['body'] = out['body'].replace('\r\n', '\n')
        return out

    def download_remote(self, address):
        r"""Download remote data to the specified local address."""
        data_dict = self.remote2local(self.remote_data)
        with open(address, 'w') as fd:
            json.dump(data_dict, fd)

    def upload_remote(self, data, update_assignees=False,
                      suspend_progress_automation=False):
        r"""Upload new data to the remote.

        Args:
            data (dict): Data that should be uploaded.
            update_assignees (bool, optional): If True, the assignees will
                include new assignees form the Smartsheet. If False, the
                assignees will only include those provided as an argument.
                Defaults to False.
            suspend_progress_automation (bool, optional): If True, the
                automation card for moving editted issues into the
                'In progress' column will be suspended. Defaults to False.

        """
        map_milestones = {x.title: x for x in
                          self.remote_data.get_milestones(state='all')}
        map_issues = {x.title: x for x in
                      self.remote_data.get_issues(state='all')}
        # Suspend automation card
        if suspend_progress_automation:
            self.suspend_card('In progress')
        # Update milestones
        for x_orig in data['milestones']:
            # Create a copy with adjustments for actually calling
            x = copy.deepcopy(x_orig)
            x['due_on'] = datetime.datetime.strptime(
                x['due_on'], "%m/%d/%y").replace(hour=8)
            # Check to see if the milestone already exists
            if x['title'] in map_milestones:
                x_obj = map_milestones[x['title']]
                diff = utils.get_diff(self.remote2local_milestone(x_obj),
                                      x_orig)
                if diff:
                    print(("Milestone '%s' already exists. Should it be "
                           "updated? The diff is \n%s\n") % (x['title'], diff))
                    if (input('y/[n]?: ').lower() in ['y', 'yes']):
                        x_obj.edit(**x)
            # Create a new milestone after confirming with the user
            else:
                print('Create new milestone?\n%s\n' % pprint.pformat(x))
                if (input('y/[n]?: ').lower() in ['y', 'yes']):
                    x_obj = self.remote_data.create_milestone(**x)
        # Update issues
        for x_orig in data['issues']:
            # Create a copy with adjustments for actually calling
            x = copy.deepcopy(x_orig)
            if x['milestone'] is None:
                continue
            x['milestone'] = map_milestones[x['milestone']]
            # Check to see if the issue already exists
            if x['title'] in map_issues:
                x_obj = map_issues[x['title']]
                if (not x['assignees']) or (not update_assignees):
                    x_orig['assignees'] = [a.login for a in x_obj.assignees]
                    x['assignees'] = x_orig['assignees']
                diff = utils.get_diff(self.remote2local_issue(x_obj), x_orig)
                if diff:
                    print(("Issue '%s' already exists. Should it be updated? "
                           "The diff is \n%s\n") % (x['title'], diff))
                    if (input('y/[n]?: ').lower() in ['y', 'yes']):
                        x_obj.edit(**x)
            # Create a new issue after confirming with the user
            else:
                x.pop('state')
                print('Create new issue?\n%s\n' % pprint.pformat(x))
                if (input('y/[n]?: ').lower() in ['y', 'yes']):
                    return self.remote_data.create_issue(**x)
        # Restore automation card
        if suspend_progress_automation:
            self.restore_card('In progress')

    @classmethod
    def get_milestone_from_Smartsheet_objective(cls, objective):
        r"""Get a dictionary representing a Github milestone from a Smartsheet
        objective.

        Args:
            objective (dict): Data from a Smartsheet objective.

        Returns:
            dict: Data comprising a Github milestone.

        """
        out = {'title': objective['Task Name'].split(': ')[0],
               'description': objective['Task Name'].split(': ')[-1],
               'state': 'open',
               'due_on': objective['Finish']}
        if objective['Status'] == 'Complete':
            out['state'] = 'closed'
        return out

    def get_issue_from_Smartsheet_milestone(self, milestone,
                                            existing_tasks=None,
                                            existing_info=None,
                                            assignees=None,
                                            update_assignees=False):
        r"""Get a dictionary representing a Github issue from a Smartsheet
        milestone.

        Args:
            milestone (dict): Data from a Smartsheet milestone.
            existing_tasks (str, optional): Tasks already present in the issue
                that should be preserved. Defaults to None and will only be
                set if the milestone 'Status' is 'In Progress'.
            existing_info (str, optional): Pre-existing lines in the
                'Additional Information' section that should be preserved.
                Defaults to ''.
            assignees (list, optional): List of assignees that should be added
                to the issue. Defaults to empty list.
            update_assignees (bool, optional): If True, the assignees will
                include new assignees form the Smartsheet. If False, the
                assignees will only include those provided as an argument.
                Defaults to False.

        Returns:
            dict: Data comprising a Github issue.

        """
        if existing_tasks is None:
            if milestone['Status'] == 'In Progress':
                existing_tasks = '- [ ] Add tasks'
            else:
                existing_tasks = ''
        if existing_info is None:
            existing_info = ''
        if assignees is None:
            assignees = []
        out = {'title': milestone['Task Name'],
               'body': _github_issue_format.format(
                   existing_tasks=existing_tasks, existing_info=existing_info,
                   **milestone),
               'milestone': milestone['Supporting Objective'],
               'assignees': assignees}
        # Assign issues to the reocrded PI and collaborators
        primary = self.names.name2github(milestone['Assigned To'])
        collab = [self.names.abbrev2github(x.strip()) for x in
                  milestone['Collaborator'].split(',')]
        # Uncomment this when people are added
        if update_assignees:
            for x in [primary] + collab:
                if x and (x not in out['assignees']):
                    out['assignees'].append(x)
        # Set status
        if milestone['Status'] == 'Complete':
            out['state'] = 'closed'
        else:
            out['state'] = 'open'
        return out

    def update_from_smartsheet(self, prev, other, update_assignees=False,
                               suspend_progress_automation=False):
        r"""Return a version of the local data updated with data from the
        provided Smartsheet data dictionary.

        Args:
            prev (dict): Github data dictionary to update.
            other (dict): Smartsheet data dictionary to update from.
            update_assignees (bool, optional): If True, the assignees will
                include new assignees form the Smartsheet. If False, the
                assignees will only include those provided as an argument.
                Defaults to False.
            suspend_progress_automation (bool, optional): If True, the
                automation card for moving editted issues into the
                'In progress' column will be suspended. Defaults to False.

        Returns:
            dict: Updated version of prev.

        """
        map_milestones = {x['title']: x for x in prev['milestones']}
        map_issues = {x['title']: x for x in prev['issues']}
        # Update Github milestones from Smartsheet supporting objectives
        for x_sm in other.local_data['objectives']:
            x_gh = self.get_milestone_from_Smartsheet_objective(x_sm)
            y_gh = map_milestones.get(x_gh['title'], None)
            if y_gh is None:
                prev['milestones'].append(x_gh)
            else:
                y_gh.update(x_gh)
        # Update Github issues from Smartsheet milestones
        for x_sm in other.local_data['milestones']:
            x_gh = self.get_issue_from_Smartsheet_milestone(
                x_sm, update_assignees=update_assignees)
            y_gh = map_issues.get(x_gh['title'], None)
            if y_gh is None:
                prev['issues'].append(x_gh)
            else:
                existing = {}
                other.get_milestone_from_Github_issue(y_gh, existing=existing)
                x_gh = self.get_issue_from_Smartsheet_milestone(
                    x_sm, update_assignees=update_assignees, **existing)
                y_gh.update(x_gh)
        return prev

    def sort_cards(self, column_name=None):
        r"""Sort cards alphabetically, putting automation cards at the bottom.

        Args:
            column_name (str, optional): Name of the column that should be
                sorted. None causes all columns to be sorted. Defaults to None.

        """
        regex_obj = '([0-9]+)([A-Z]+)([0-9]+):'
        if column_name is None:
            column_name = list(self.github_project.get_columns())
        if isinstance(column_name, list):
            for column in column_name:
                self.sort_cards(column)
            return
        elif isinstance(column_name, github.ProjectColumn.ProjectColumn):
            column = column_name
        else:
            column = self.get_entry(self.github_project.get_columns(), 'name',
                                    column_name, by_attr=True)
        keymap = ('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                  'abcdefghijklmnopqrstuvwxyz')

        def sort_cards(card):
            if card.note:
                if card.note.startswith('###### Automation Rules'):
                    return 'zzzz' + card.note
                return '0000' + card.note
            else:
                issue_name = card.get_content().title
                matches = re.findall(regex_obj, issue_name)
                if matches:
                    return ''.join([keymap[int(matches[0][0])], matches[0][1],
                                    keymap[int(matches[0][2])]])
                return '0000' + issue_name

        cards = sorted(list(column.get_cards()), key=sort_cards)
        self.edit_card(cards[0], position='top')
        for i in range(1, len(cards)):
            self.edit_card(cards[i], position=('after:%s'
                                               % cards[i - 1].id))

    def get_card(self, column_name=None, card_prefix=None, issue=None,
                 return_column=False, default=False):
        r"""Located a project card.

        Args:
            column_name (str, optional): Name of the column where the desired
                card is located. Providing None will cause the search to be
                accross all columns. Defaults to None.
            card_prefix (str, optional): Start of the card that should be
                returned. Defaults to None and is ignored.
            issue (github.Issue.Issue, optional): Github issue that associated
                card should be located. Defaults to Noen and is ignored.
            return_column (bool, optional): If True, the column containing the
                card is returned instead of the card itself. Defaults to False.
            default (object, optional): Entry that should be returned if a
                match cannot be located. Defaults to False and an error will be
                raised if a match cannot be found.

        Returns:
            github.ProjectCard.ProjectCard: Project card.

        Raises:
            ValueError: If nither card_prefix or issue are provided.
            ValueError: If the card cannot be located and default is False.

        """
        if (card_prefix is None) and (issue is None):
            raise ValueError("Either card_prefix or issue must be provided.")
        if column_name is None:
            column_list = self.github_project.get_columns()
        elif isinstance(column_name, github.ProjectColumn.ProjectColumn):
            column_list = [column_name]
        elif isinstance(column_name, list):
            column_list = column_name
        else:
            column_list = [self.get_entry(self.github_project.get_columns(),
                                          'name', column_name, by_attr=True)]
        card = None
        kwargs = {'default': None}
        if card_prefix is not None:
            def func_validate(a, b):
                if a is None:
                    return False
                return a.startswith(b)

            kwargs.update(key='note', value=card_prefix,
                          by_attr=True, func_validate=func_validate)
        elif issue is not None:
            def func_validate(a, b):
                return (a() == b)

            kwargs.update(key='get_content', value=issue,
                          by_attr=True, func_validate=func_validate)

        for column in column_list:
            card = self.get_entry(column.get_cards(archived_state='all'),
                                  **kwargs)
            if card is not None:
                if return_column:
                    return column
                break
        if card is None:
            if default is False:
                raise ValueError("Could not locate card with name '%s'"
                                 % column_name)
            card = default
        return card

    def edit_card(self, card, note=None, archived=None,
                  position=None, column_id=None):
        r"""Edit a Github project card.

        Args:
            card (github.ProjectCard.ProjectCard): Project card.
            note (str, optional): New value for note.
            archived (str, optional): New value for archived.

        """
        # Call to PATCH
        post_parameters = dict()
        if note is not None:
            post_parameters['note'] = note
        if archived is not None:
            post_parameters['archived'] = archived
        if post_parameters:
            import_header = {"Accept": Consts.mediaTypeProjectsPreview}
            headers, data = card._requester.requestJsonAndCheck(
                "PATCH",
                card.url,
                headers=import_header,
                input=post_parameters)
            card._useAttributes(data)
        # Call to POST moves
        post_parameters = dict()
        if position is not None:
            post_parameters['position'] = position
        if column_id is not None:
            post_parameters['column_id'] = column_id
        if post_parameters:
            import_header = {"Accept": Consts.mediaTypeProjectsPreview}
            headers, data = card._requester.requestJsonAndCheck(
                "POST",
                card.url + '/moves',
                headers=import_header,
                input=post_parameters)
            card._useAttributes(data)

    def suspend_card(self, column_name, card_prefix='###### Automation Rules'):
        r"""Suspend automation card.

        Args:
            column_name (str): Name of the column where the automattion card is
                located.
            card_prefix (str, optional): Start of the card that should be
                suspended. Defaults to '###### Automation Rules'.

        """
        card = self.get_card(column_name=column_name, card_prefix=card_prefix)
        self.edit_card(card, archived=True)

    def restore_card(self, column_name, card_prefix='###### Automation Rules'):
        r"""Restore automation card.

        Args:
            column_name (str): Name of the column where the automattion card is
                located.
            card_prefix (str, optional): Start of the card that should be
                restored (this should be the original, without comments).
                Defaults to '###### Automation Rules'.

        """
        card = self.get_card(column_name=column_name, card_prefix=card_prefix)
        self.edit_card(card, archived=False, position='bottom')


class SmartsheetAPI(UpdateAPI):

    name = 'smartsheet'

    def __init__(self, *args, **kwargs):
        self._contacts = None
        super(SmartsheetAPI, self).__init__(*args, **kwargs)

    @property
    def remote_address_default(self):
        r"""str: The address associated with the remote project data."""
        return self.config['smartsheet']['sheet']

    @property
    def contacts(self):
        r"""list: Contacts associated with the sheet."""
        if self._contacts is None:
            self._contacts = self.api.Contacts.list_contacts(
                include_all=True).data
        return self._contacts

    @property
    def users(self):
        r"""list: Users associated with the sheet."""
        if self._users is None:
            self._users = self.api.Users.list_users(
                include_all=True).data
        return self._users

    @classmethod
    def get_api(cls, token=None):
        r"""Return the top level API object."""
        smart = smartsheet.Smartsheet(token)
        smart.errors_as_exceptions(True)
        return smart

    @classmethod
    def load_local(cls, address, default=False):
        r"""Get the local data for the specified address."""
        if isinstance(address, str):
            assert(os.path.isfile(address))
            fd = open(address, newline='')
        else:
            fd = address
        unused_fields = ['Duration', 'Predecessors']
        goals = []
        objectives = []
        milestones = []
        # Read
        try:
            reader = csv.DictReader(fd)
            objective = None
            for row in reader:
                if row['Task Name'].startswith('Goal'):
                    goals.append(row)
                elif row['Task Name'].startswith('Supporting objective'):
                    objective = row
                    objectives.append(objective)
                else:
                    func = GithubAPI.get_milestone_from_Smartsheet_objective
                    row['Supporting Objective'] = func(objective)['title']
                    for k in unused_fields:
                        row.pop(k)
                    milestones.append(row)
        finally:
            if isinstance(address, str):
                fd.close()
        return {'goals': goals, 'objectives': objectives,
                'milestones': milestones}

    def load_remote(self, address, default=False):
        r"""Get the remote data for the specified address."""
        sheet_list = self.api.Sheets.list_sheets(include_all=True)
        try:
            out = self.get_entry(sheet_list.result, 'name', address,
                                 by_attr=True)
            return self.api.Sheets.get_sheet(out.id)
        except ValueError:
            if default is not False:
                return default
            raise

    def download_remote(self, address):
        r"""Download remote data to the specified local address."""
        fname_dir = os.path.dirname(address)
        fname_download = os.path.join(fname_dir, self.remote_data.name)
        fname_download += '.csv'
        self.api.Sheets.get_sheet_as_csv(self.remote_data.id, fname_dir)
        assert(os.path.isfile(fname_download))
        shutil.move(fname_download, address)

    def upload_remote(self, data):
        r"""Upload new data to the remote.

        Args:
            data (dict): Data that should be uploaded.

        """
        title_key = 'Task Name'
        # Create maps from strings to Smartsheet objects
        columns_map = OrderedDict()
        for col in self.remote_data.columns:
            columns_map[col.title] = col
        contacts_map = {}
        for contact in self.contacts:
            contacts_map[contact.name] = contact
        if not contacts_map:
            raise ValueError(("Your contacts list is empty. Upload contacts "
                              "from the contacts files: %s")
                             % self.config['general']['contacts_file'])
        rows_map = {}
        updated_rows = []
        for row in self.remote_data.rows:
            title_cell = row.get_column(columns_map[title_key].id)
            rows_map[title_cell.value] = row
        # for x_orig in data['objectives'] + data['milestones']:
        for x_orig in data['milestones']:
            assert(x_orig[title_key] in rows_map)
            irow_prev = rows_map[x_orig[title_key]]
            irow = smartsheet.models.Row()
            irow.id = irow_prev.id
            for k in columns_map.keys():
                if k not in x_orig:
                    continue
                v = x_orig[k]
                objv = None
                # YYYY-MM-DDTHH:MM:SSZ ISO 8601 format required
                if k in ['Start', 'Finish']:
                    t = datetime.datetime.strptime(v, "%m/%d/%y").replace(
                        hour=8)
                    v = t.isoformat()
                    if k in ['Finish']:
                        continue
                elif k in ['Assigned To']:
                    if v not in contacts_map:
                        raise ValueError("No contact associated with name: %s"
                                         % v)
                    objv = contacts_map[v]
                    v = objv.email
                icell_prev = irow_prev.get_column(columns_map[k].id)
                icell = smartsheet.models.Cell()
                icell.column_id = columns_map[k].id
                icell.value = v
                if objv is not None:
                    icell.objectValue = objv
                icell.strict = True
                if (((icell.value != icell_prev.value)
                     and (icell.value or icell_prev.value))):
                    irow.cells.append(icell)
            if len(irow.cells):
                updated_rows.append(irow)
        if updated_rows:
            updated_rows = self.api.Sheets.update_rows(
                self.remote_data.id, updated_rows)

    @classmethod
    def get_objective_from_Github_milestone(cls, milestone):
        r"""Get a Smartsheet objective form a Github milestone.

        Args:
            milestone (dict): Data from a Github milestone.

        Returns:
            dict: Data for a Smartsheet objective.

        """
        out = {'Task Name': '%s: %s' % (milestone['title'],
                                        milestone['description']),
               'Finish': milestone['due_on']}
        if milestone['state'] == 'closed':
            out['Status'] = 'Complete'
        return out

    @classmethod
    def get_milestone_from_Github_issue(cls, issue, existing=None):
        r"""Get a Smartsheet milestone from a Github issue.

        Args:
            issue (dict): Data from a Github issue.
            existing (dict, optional): Dictionary that will be updated with
                existing data not covered by the Smartsheet milestone. Defaults
                to None.

        Returns:
            dict: Data for a Smartsheet milestone.

        """
        if existing is None:
            existing = {}
        existing['assignees'] = issue['assignees']
        # Parse issue body to get milestone
        body = issue['body'].replace('\r\n', '\n')
        regex_entry = r'([ ]?)\{([^\}]+)\}'
        regex_body = _github_issue_format.replace('(', '\(').replace(
            ')', '\)')
        field_order = []
        for lead, x in re.findall(regex_entry, _github_issue_format):
            field_order.append(x)
            x_fmt = '{%s}' % x
            x_rgx = '(.*|\B)?'
            if lead:
                x_fmt = lead + x_fmt
                x_rgx = '(?:[ ]?)' + x_rgx
            regex_body = regex_body.replace(x_fmt, x_rgx)
        # print('body:\n%s%s' % (body, 80*'='))
        # print('format:\n%s%s' % (_github_issue_format, 80*'='))
        # print("regex:\n%s%s" % (regex_body, 80*'='))
        field_values = re.findall(regex_body, body, flags=re.DOTALL)
        if not field_values:
            raise Exception("Failed to parse body.")
        assert(len(field_values[0]) == len(field_order))
        out = {k: v for k, v in zip(field_order, field_values[0])}
        # pprint.pprint(out)
        for k in field_order:
            if k.startswith('existing_'):
                existing[k] = out.pop(k)
        # Update milestone with other information from the issue
        out.update({'Task Name': issue['title'],
                    'Supporting Objective': issue['milestone']})
        ncomplete = issue['body'].count('- [X]')
        ntask = ncomplete + issue['body'].count('- [ ]')
        if issue['state'] == 'closed':
            out['Status'] = 'Complete'
        elif ntask > 0:
            # out['Status'] = 'In Progress (%d/%d)' % (ncomplete, ntask)
            out['Status'] = 'In Progress'
        return out

    def update_from_github(self, prev, other):
        r"""Return a version of the local data updated with data from the
        provided Github data dictionary.

        Args:
            prev (dict): Smartsheet data dictionary to update.
            other (dict): Github data dictionary to update from.

        Returns:
            dict: Updated version of prev.

        """
        map_objectives = {x['Task Name']: x for x in prev['objectives']}
        map_milestones = {x['Task Name']: x for x in prev['milestones']}
        # Create mapping from issue titles to columns & cards
        column_list = other.github_project.get_columns()
        card_map = {}
        for col in column_list:
            for card in col.get_cards(archived_state='all'):
                issue = card.get_content()
                if (issue is not None) and (issue.title in map_milestones):
                    card_map[issue.title] = {'column': col,
                                             'card': card,
                                             'issue': issue}
        # Update Smartsheet objectives from Github milestones
        for x_gh in other.local_data['milestones']:
            x_sm = self.get_objective_from_Github_milestone(x_gh)
            y_sm = map_objectives.get(x_sm['Task Name'], None)
            if y_sm is None:
                prev['objectives'].append(x_sm)
            else:
                y_sm.update(x_sm)
        # Update Smartsheet milestones from Github issues
        for x_gh in other.local_data['issues']:
            if x_gh['title'] not in map_milestones:
                self.logger.info("Non-milestone issue: '%s'" % x_gh['title'])
                continue
            x_sm = self.get_milestone_from_Github_issue(x_gh)
            y_sm = map_milestones.get(x_sm['Task Name'], None)
            column = card_map[x_gh['title']]['column'].name
            if column == 'In progress':
                x_sm['Status'] = 'In Progress'
            elif column == 'Done':
                x_sm['Status'] = 'Complete'
            if y_sm is None:
                if x_sm['Supporting Objective'] is not None:
                    prev['milestones'].append(x_sm)
            else:
                y_sm.update(x_sm)
        return prev
