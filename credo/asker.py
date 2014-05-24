from credo.errors import BadConfigFile, BadCredentialSource, CredoProgrammerError, UserQuit

import ConfigParser
import getpass
import logging
import keyring
import boto
import sys
import os

log = logging.getLogger("credo.asker")

def get_response(*messages, **kwargs):
    """Get us a response from the user"""
    password = kwargs.get("password", False)
    if password:
        prompt = kwargs.get("prompt", ":")
    else:
        prompt = kwargs.get("prompt", ": ")

    for message in messages:
        if isinstance(message, dict):
            for num, val in message.items():
                print >> sys.stderr, "{0}) {1}".format(num, val)
        else:
            print >> sys.stderr, message

    if prompt:
        sys.stderr.write(str(prompt))
        sys.stderr.flush()

    try:
        if password:
            return getpass.getpass("")
        else:
            return raw_input()
    except KeyboardInterrupt:
        raise UserQuit()
    except EOFError:
        raise UserQuit()

def ask_for_choice(message, choices):
    """Ask for a value from some choices"""
    mapped = dict(enumerate(sorted(choices)))
    no_value = True
    while no_value:
        response = get_response(message, "Please choose a value from the following", mapped)

        if response is None or not response.isdigit() or int(response) not in mapped:
            print >> sys.stderr, "Please choose a valid response ({0} is not valid)".format(response)
        else:
            no_value = False
            return mapped[int(response)]

def ask_for_choice_or_new(needed, choices):
    mapped = dict(enumerate(sorted(choices)))
    while True:
        if mapped:
            maximum = max(mapped.keys())
            response = get_response(
                  "Choose a {0}".format(needed), "Please choose a value from the following"
                , mapped, {maximum+1: "Make your own value"}
                )

            if response is None or not response.isdigit() or int(response) < 0 or int(response) > maximum + 1:
                print >> sys.stderr, "Please choose a valid response ({0} is not valid)".format(response)
                continue
            else:
                response = int(response)
                if response in mapped:
                    return mapped[response]

        return get_response(prompt="Enter your custom value: ")

secret_sources = {
      "specified": "Specify your own value"
    , "aws_config": "Your awscli config file"
    , "boto_config": "Your boto config file"
    , "environment": "Your current environment"
    }

def ask_user_for_secrets(source=None):
    """Ask the user for access_key and secret_key"""
    choices = []
    access_key_name = "AWS_ACCESS_KEY_ID"
    secret_key_name = "AWS_SECRET_ACCESS_KEY"

    environment = os.environ

    if access_key_name in environment and secret_key_name in environment:
        choices.append(secret_sources["environment"])

    if os.path.exists(os.path.expanduser("~/.aws/config")):
        choices.append(secret_sources["aws_config"])

    if os.path.exists(os.path.expanduser("~/.boto")):
        choices.append(secret_sources["boto_config"])

    val = None
    if not source:
        if choices:
            val = ask_for_choice("Method of getting keys", choices + [secret_sources["specified"]])
        else:
            val = secret_sources["specified"]
    else:
        if source not in secret_sources.keys() and source not in secret_sources.values():
            raise BadCredentialSource("Unknown credential source", source=source)

        if source in secret_sources:
            source = secret_sources[source]

        log.info("Getting credentials from %s", source)

    if secret_sources["specified"] in (val, source):
        access_key = get_response(prompt="Access key: ")
        secret_key = get_response(prompt="Secret key: ")

    elif secret_sources["environment"] in (val, source):
        if access_key_name not in environment or secret_key_name not in environment:
            raise BadCredentialSource("Couldn't find environment variables for {0} and {1}".format(access_key_name, secret_key_name))
        access_key = environment[access_key_name]
        secret_key = environment[secret_key_name]

    elif secret_sources["boto_config"] in (val, source) or secret_sources["aws_config"] in (val, source):
        parser = ConfigParser.SafeConfigParser()
        aws_location = os.path.expanduser("~/.aws/config")
        boto_location = os.path.expanduser("~/.boto")

        if source == secret_sources["aws_config"] and not os.path.exists(aws_location):
            raise BadCredentialSource("Couldn't find the aws config", location=aws_location)
        if source == secret_sources["boto_config"] and not os.path.exists(boto_location):
            raise BadCredentialSource("Couldn't find the boto config", location=boto_location)

        if secret_sources["boto_location"] in (val, source):
            location = boto_location
        else:
            location = aws_location

        # Read it in
        parser.read(location)

        # Find possilbe sections
        sections = []
        for section in boto.config.sections():
            if section in ("Credentials", "default"):
                sections.append(section)

            elif section.startswith("profile "):
                sections.append(section)

        # Get sections that definitely have secrets
        sections_with_secrets = []
        for section in sections:
            if parser.has_option(section, "aws_access_key_id") and (parser.has_option(section, "aws_secret_access_key") or parser.has_option(section, "keyring")):
                sections_with_secrets.append(section)

        if not sections:
            raise BadConfigFile("No secrets to be found in the amazon config file", location=location)
        elif len(sections) == 1:
            section = sections[0]
        else:
            section = ask_for_choice("Which section to use?", sections)

        access_key = parser.get(section, "aws_access_key_id")
        if parser.has_option(section, "aws_secret_access_key"):
            secret_key = parser.get(section, "aws_secret_access_key")
        else:
            keyring_name = parser.get(section, 'keyring')
            secret_key = keyring.get_password(keyring_name, access_key)
    else:
        raise CredoProgrammerError("Not possible to reach this point", source=source)

    return access_key, secret_key

