from urllib.parse import urlparse
from pecan import conf
from pecan.jsonify import jsonify
from pymongo import MongoClient, TEXT

import time
import re
import json
import mf2py
import mf2util


# Connect to the database
client = MongoClient(conf.database.url)
db = client.identities
db.identities.create_index([
    ('url', TEXT),
    ('name', TEXT),
    ('nicknames', TEXT),
    ('pseudonyms.username', TEXT)
])


class Pseudonym:
    '''
    Base class representing a "pseudonym" for an identity.

    Subclasses simply set a "target" ('twitter', 'instagram')
    property and a "regex" property (a compiled regex which can
    be used to parse out the username on the target).

    There is an `identify_url` classmethod that can be used to
    find the matching pseudonym for a specific URL.
    '''

    registry = {}

    def __init_subclass__(cls, **kw):
        cls.registry[cls.target] = cls

    def __init__(self, url, parent, username=None):
        self.url = url
        self.parent = parent
        self.username = username

    @property
    def matches(self):
        match = self.regex.match(self.url)
        if not match:
            return False

        self.username = match.groups()[1].replace('/', '')

        return True

    @classmethod
    def identify_url(cls, url, parent):
        for PseudonymCls in cls.registry.values():
            pseudonym = PseudonymCls(url, parent)
            if pseudonym.matches:
                return pseudonym

    @property
    def mention_text(self):
        return '@' + self.username

    @property
    def mention_html(self):
        name = self.parent.name or ('@' + self.username)
        return '<a href="' + self.url + '">' + name + '</a>'

    def __json__(self):
        return {
            'url': self.url,
            'username': self.username,
            'target': self.target
        }

    @classmethod
    def from_json(cls, data, parent):
        PseudonymCls = cls.registry[data['target']]
        return PseudonymCls(
            url=data['url'],
            parent=parent,
            username=data['username']
        )



class TwitterPseudonym(Pseudonym):
    target = 'twitter'
    regex = re.compile(r'^https?\:\/\/(www\.)?twitter.com\/([\S]+\.?)')

    @property
    def matches(self):
        match = super().matches
        if match:
            self.username = self.username.replace('intentuser?screen_name=', '')
        return match


class InstagramPseudonym(Pseudonym):
    target = 'instagram'
    regex = re.compile(r'^https?\:\/\/(www\.)?instagram.com\/([\S]+\.?)')


class MicroblogPseudonym(Pseudonym):
    target = 'micro.blog'
    regex = re.compile(r'^https?\:\/\/(www\.)?micro.blog\/([\S]+\.?)')


class LinkedInPseudonym(Pseudonym):
    target = 'linkedin'
    regex = re.compile(r'^https?\:\/\/(www\.)?linkedin.com\/in\/([\S]+\.?)')


class GitHubPseudonym(Pseudonym):
    target = 'github'
    regex = re.compile(r'^https?\:\/\/(www\.)?github.com\/([\S]+\.?)')


class KeybasePseudonym(Pseudonym):
    target = 'keybase'
    regex = re.compile(r'^https?\:\/\/(www\.)?keybase.io\/([\S]+\.?)')



class Identity:
    '''
    Represents an IndieWeb website (URL) which is properly marked up
    with microformats2, including rel-me links for each pseudonym,
    and a representative h-card (optional) which can be used to
    identify a name for this identity.
    '''

    def __init__(self, url, fetch=True):
        parsed_url = urlparse(url)
        if parsed_url.scheme not in ('http', 'https'):
            raise 'Please provide an HTTP or HTTPS URL'

        if parsed_url.path == '':
            url = parsed_url.geturl() + '/'
        else:
            url = parsed_url.geturl()

        self.url = url
        self.pseudonyms = {}
        self.name = None
        self.nicknames = None
        self.timestamp = None

        if fetch:
            self.fetch()

    def fetch(self):
        # fetch the website and parse for microformats
        try:
            parser = mf2py.Parser(url=self.url)
        except:
            return None

        # identify the representative h-card
        parsed = parser.to_dict()
        hcard = mf2util.representative_hcard(parsed, self.url)

        if not hcard:
            hcards = parser.to_dict(filter_by_type='h-card')
            if len(hcards):
                hcard = hcards[0]

        if hcard:
            self.name = hcard['properties'].get('name', [None])[0]
            self.nicknames = hcard['properties'].get('nickname', None)

        # identify rel-me links as pseudonyms
        matches = {}
        for url in parser.to_dict()['rels'].get('me', []):
            match = Pseudonym.identify_url(url, self)
            if not match:
                continue
            if match.target not in self.pseudonyms:
                self.pseudonyms[match.target] = match

        # remember the last time I fetched
        self.timestamp = time.time()

        # save to the database
        self.save()

    def save(self):
        identity = db.identities.find_one({'url': self.url})
        if identity:
            db.identities.replace_one(
                {'url': self.url},
                jsonify(self)
            )
        else:
            db.identities.insert_one(jsonify(self))

    def __json__(self):
        return {
            'timestamp': self.timestamp,
            'url': self.url,
            'name': self.name,
            'nicknames': self.nicknames,
            'pseudonyms': [
                jsonify(p) for p in self.pseudonyms.values()
            ]
        }

    @classmethod
    def from_json(cls, data):
        identity = cls(data['url'], fetch=False)
        identity.name = data['name']
        identity.nicknames = data['nicknames']
        identity.timestamp = data['timestamp']
        for pseudonym_data in data['pseudonyms']:
            pseudonym = Pseudonym.from_json(pseudonym_data, identity)
            identity.pseudonyms[pseudonym.target] = pseudonym
        return identity

    @classmethod
    def find_or_fetch(cls, url, force=False):
        parsed_url = urlparse(url)
        if parsed_url.scheme not in ('http', 'https'):
            return None

        if parsed_url.path == '':
            url = parsed_url.geturl() + '/'
        else:
            url = parsed_url.geturl()

        if not force:
            identity_doc = db.identities.find_one({'url': url})
            if identity_doc:
                if (time.time() - identity_doc['timestamp']) < conf.database.cache_seconds:
                    return cls.from_json(identity_doc)

        return cls(url, fetch=True)

    @classmethod
    def search(cls, term):
        results = db.identities.find({'$text': {'$search': term}})
        return [
            Identity.from_json(doc)
            for doc in results
        ]


class Content:
    '''
    Content that may contain an @{} mention.
    '''

    regex = re.compile(r'@{([\S]+)}')

    def __init__(self, content):
        self.content = content

    def transform(self):
        versions = {
            'original': {
                'text': self.content,
                'html': self.content
            }
        }

        matches = self.regex.findall(self.content)
        if not matches:
            return versions

        for match in matches:
            try:
                parsed_url = urlparse(match)
            except:
                continue

            if parsed_url.scheme not in ('http', 'https'):
                url = 'https://' + match
                try:
                    parsed_url = urlparse(url)
                except:
                    continue

            if parsed_url.path == '':
                url = parsed_url.geturl() + '/'
            else:
                url = parsed_url.geturl()

            identity = Identity(url)

            for pseudonym in identity.pseudonyms.values():
                if pseudonym.target not in versions:
                    versions[pseudonym.target] = {
                        'text': self.content,
                        'html': self.content
                    }

                text = versions[pseudonym.target]['text']
                html = versions[pseudonym.target]['html']
                versions[pseudonym.target]['text'] = text.replace(
                    '@{' + match + '}',
                    pseudonym.mention_text
                )
                versions[pseudonym.target]['html'] = html.replace(
                    '@{' + match + '}',
                    pseudonym.mention_html
                )

        return versions
