import os
import sys
import glob
import shutil


# TODO: interface with repo
def fix_paths(search_dir):
    if sys.platform not in ['win32', 'cygwin']:
        files = glob.glob(search_dir + '\\*')
        for f in files:
            shutil.move(f, os.path.join(search_dir,
                                        f.split(search_dir + '\\')[-1]))
