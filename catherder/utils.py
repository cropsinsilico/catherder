import os
import json
import glob
import tempfile
import pprint
import difflib
import logging
from github.GithubException import UnknownObjectException
import names
logger = logging.getLogger('CiS2.0')


def find_most_recent(fname_format, repo=None, return_tempfile=False):
    if repo is None:
        fname_glob = fname_format.replace(names.time_format, '*')
        all_files = sorted(glob.glob(fname_glob))
        if all_files:
            return all_files[-1]
    else:
        try:
            all_files = sorted(
                repo.get_dir_contents(os.path.dirname(fname_format)),
                key=lambda x: getattr(x, 'path'))
            if all_files:
                contents = all_files[-1].decoded_content
                if return_tempfile:
                    ext = os.path.splitext(fname_format)[-1]
                    out = tempfile.NamedTemporaryFile(suffix=ext, mode='r+')
                    out.write(contents.decode('utf-8'))
                    out.seek(0)
                    return out
                elif fname_format.endswith('.json'):
                    out = json.loads(contents)
                else:
                    out = contents
                return out
        except UnknownObjectException:
            pass
    return None


def get_diff(a, b, nlines_context=5):
    r"""Get difference between two objects by comparing their pprint strings.

    Args:
        a (obj): First object for comparison.
        b (obj): Second object for comparison.
        nlines_context (int, optional): Number of lines before or after a
            difference that should be included in returned diff. Defaults to 5.

    Returns:
        str, bool: If there are not any differences between the two objects,
            False is returned. If there are differences, the diff is returned
            as a string.

    """
    if isinstance(a, (str, bytes)):
        if os.path.isfile(a):
            with open(a, 'rb') as fd:
                if a.endswith('.json'):
                    a = json.load(fd)
                else:
                    a = fd.read().splitlines(keepends=True)
        else:
            a = a.splitlines(keepends=True)
    str_a = pprint.pformat(a).splitlines(keepends=True)
    if isinstance(b, (str, bytes)):
        if os.path.isfile(b):
            with open(b, 'rb') as fd:
                if b.endswith('.json'):
                    b = json.load(fd)
                else:
                    b = fd.read().splitlines(keepends=True)
        else:
            b = b.splitlines(keepends=True)
    str_b = pprint.pformat(b).splitlines(keepends=True)
    diff = list(difflib.unified_diff(str_a, str_b))
    # diff = list(difflib.ndiff(str_a, str_b))
    if not any([x.startswith(('-', '+', '?')) for x in diff]):
        return False
    # return pprint.pformat(diff)
    return ''.join(diff)
