from credo.errors import NoConfigFile, BadConfigFile, CredoError, BadConfiguration
from credo.asker import ask_for_choice, ask_for_choice_or_new
from credo.loader import CredentialInfo, Loader
from credo.explorer import Explorer

import json
import os

class Unspecified(object):
    """Telling the difference between None and just not specified"""

class Credo(object):
    """Incredible credo knows all"""

    def __init__(self, crypto):
        self.crypto = crypto

    @property
    def chosen(self):
        """Return our chosen creds"""
        if not hasattr(self, "_chosen"):
            self._chosen = self.find_credentials()
            self.add_public_keys(self.repo, self.crypto)
            self.set_options(repo=self._chosen.credential_info.repo, account=self._chosen.credential_info.account, user=self._chosen.credential_info.user)
        return self._chosen

    @property
    def can_encrypt(self):
        """Say whether we have any public keys to encrypt with"""
        return self.crypto.has_public_keys()

    def make_explorer(self):
        """Make us an explorer"""
        return Explorer(self.root_dir, self.crypto)

    def find_credentials(self, completed=None, chain=None, chosen=None):
        """
        Traverse our directory structure, asking as necessary

        and return the credentials object we find
        """
        if completed is None:
            completed, _ = self.make_explorer().filtered(repo=self.repo, account=self.account, user=self.user)

        if chain is None:
            chain = [("repo", "Repository"), ("account", "Account"), ("user", "User")]

        if chosen is None:
            chosen = []

        nxt, category = chain.pop(0)
        if len(completed) is 1:
            val = completed.keys()[0]
        else:
            if not completed:
                raise CredoError("Told to find a key that doesn't exist", repo=self.repo, account=self.account, user=self.user)
            val = ask_for_choice(category, sorted(completed.keys()))

        chosen.append((nxt, val))
        if not chain:
            return completed[val]
        else:
            return self.find_credentials(completed[val], list(chain), list(chosen))

    def make_credentials(self, directory_structure=None, chain=None, chosen=None):
        """
        Traverse our directory structure, asking as necessary

        and create new parts of the structure as necessary
        """
        if directory_structure is None:
            directory_structure = self.make_explorer().directory_structure

        if chain is None:
            chain = [("repos", "repo", "Repository"), ("accounts", "account", "Account"), ("users", "user", "User")]

        if chosen is None:
            chosen = []

        container, nxt, category = chain.pop(0)
        if container not in directory_structure:
            directory_structure[container] = {}

        if getattr(self, nxt, None):
            val = getattr(self, nxt)
        else:
            val = ask_for_choice_or_new(category, sorted(key for key in directory_structure[container].keys() if not key.startswith('/')))
        location = os.path.join(directory_structure['/location/'], val)
        if val not in directory_structure[container]:
            directory_structure[container][val] = {'/files/': [], '/location/': location}

        chosen.append((nxt, val))
        if not chain:
            chosen.append(("location", os.path.join(location, "credentials.json")))
            credential_info = CredentialInfo(**dict(chosen))

            credentials = Loader().from_file(credential_info, self.crypto, default_type="amazon")
            if credential_info.location not in directory_structure['/files/']:
                directory_structure['/files/'].append(credential_info.location)
            directory_structure['/credentials/'] = credentials
            return credentials
        else:
            return self.make_credentials(directory_structure[container][val], list(chain), list(chosen))

    def find_options(self, config_file=Unspecified, root_dir=Unspecified, **kwargs):
        """Setup the credo!"""
        if config_file is Unspecified:
            config_file = self.find_config_file(config_file)

        if config_file:
            if not os.path.exists(config_file):
                raise NoConfigFile("Specified location is empty", location=config_file)
            if not os.access(config_file, os.R_OK):
                raise BadConfigFile("Config file isn't readable", location=config_file)

            self.read_from_config(config_file)

        # Override the root dir if supplied
        if root_dir is not Unspecified:
            self.root_dir = root_dir

        self.set_options(**kwargs)

    def set_options(self, **kwargs):
        """Set specific options"""
        if not getattr(self, "user", None) and not getattr(self, "account", None) and kwargs.get("creds"):
            creds = kwargs["creds"]
            if '@' not in creds:
                raise BadConfiguration("Creds option needs to be user@account", got=creds)

            user, account = creds.split("@")
            self.user = user.strip()
            self.account = account.strip()

        for attribute in ("user", "account", "repo"):
            if not getattr(self, attribute, None) and attribute in kwargs:
                setattr(self, attribute, kwargs[attribute])

    def find_config_file(self, config_file=Unspecified):
        """Find a config file, use the one given if specified"""
        if config_file is not Unspecified:
            return config_file

        credo_home = os.path.expanduser("~/.credo")
        home_config = os.path.join(credo_home, "config.json")
        if os.path.exists(home_config) and os.stat(home_config).st_size > 0:
            return home_config

        if not os.path.exists(credo_home):
            os.makedirs(credo_home)
        json.dump({"root_dir": os.path.expanduser("~/.credo/repos")}, open(home_config, "w"))
        return home_config

    def read_from_config(self, config_file):
        """Call find_options using options from the config file"""
        # What's an error handling?
        options = json.load(open(config_file))
        options["config_file"] = None
        self.find_options(**options)

    def add_public_keys(self, repo, crypto):
        """Find public keys for this repo and add them to the crypto object"""
        public_key = os.path.expanduser("~/.ssh/id_rsa.pub")
        crypto.add_public_keys([open(public_key).read()])

