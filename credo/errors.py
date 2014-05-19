class CredoError(Exception):
    """Helpful class for creating custom exceptions"""
    desc = ""

    def __init__(self, message="", **kwargs):
        self.kwargs = kwargs
        self.message = message
        super(CredoError, self).__init__(message)

    def __str__(self):
        desc = self.desc
        message = self.message

        info = ["{0}={1}".format(k, v) for k, v in sorted(self.kwargs.items())]
        info = '\t'.join(info)
        if info and (message or desc):
            info = "\t{0}".format(info)

        if desc:
            if message:
                message = ". {0}".format(message)
            return '"{0}{1}"{2}'.format(desc, message, info)
        else:
            if message:
                return '"{0}"{1}'.format(message, info)
            else:
                return "{0}".format(info)

class NoExecCommand(CredoError):
    desc = "No exec command to execute"

class NoConfigFile(CredoError):
    desc = "No config file"

class BadConfigFile(CredoError):
    desc = "Bad config file"

class NotEnoughInfo(CredoError):
    desc = "Need more information"

class BadConfig(CredoError):
    desc = "Bad Config"

class BadCredentialFile(CredoError):
    desc = "Bad credentials file"

class BadSSHKey(CredoError):
    desc = "Bad ssh key"

class BadCypherText(CredoError):
    desc = "Couldn't decrypt text"

class BadConfiguration(CredoError):
    desc = "Bad configuration"

class NoCredentialsFound(CredoError):
    desc = "Couldn't find any credentials"

class BadFolder(CredoError):
    desc = "Something wrong with a folder"

class CantEncrypt(CredoError):
    desc = "Can't do encryption"

class BadPlainText(CredoError):
    desc = "Can't encrypt value"

class PasswordRequired(CredoError):
    desc = "Need a password"

class BadPrivateKey(BadSSHKey):
    desc = "Bad private ssh key"

class BadPublicKey(BadSSHKey):
    desc = "Bad public ssh key"

