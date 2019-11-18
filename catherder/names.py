import os
import csv
from catherder import config


class Names(list):
    def __init__(self, fname, key_name='Name', key_email='E-mail Address',
                 key_github='Github Username', key_abbrev='Abbreviation'):
        self.key_name = key_name
        self.key_email = key_email
        self.key_github = key_github
        self.key_abbrev = key_abbrev
        if isinstance(fname, config.str_types):
            assert(os.path.isfile(fname))
            with open(fname, newline='', encoding='utf-8-sig') as fd:
                reader = csv.DictReader(fd)
                people = [row for row in reader]
        else:
            fd = fname
            reader = csv.DictReader(fd)
            people = [row for row in reader]
        super(Names, self).__init__(people)

    def convert_name(self, key1, key2, name):
        if not name:
            return ''
        for p in self:
            if p[key1] == name:
                return p[key2]
        raise ValueError("Could not locate person with %s '%s'" % (key1, name))

    def name2email(self, name):
        return self.convert_name(self.key_name, self.key_email, name)

    def email2name(self, name):
        return self.convert_name(self.key_email, self.key_name, name)

    def name2github(self, name):
        return self.convert_name(self.key_name, self.key_github, name)

    def github2name(self, name):
        return self.convert_name(self.key_github, self.key_name, name)

    def name2abbrev(self, name):
        return self.convert_name(self.key_name, self.key_abbrev, name)

    def abbrev2name(self, name):
        return self.convert_name(self.key_abbrev, self.key_name, name)

    def abbrev2github(self, name):
        return self.convert_name(self.key_abbrev, self.key_github, name)

    def github2abbrev(self, name):
        return self.convert_name(self.key_github, self.key_abbrev, name)
