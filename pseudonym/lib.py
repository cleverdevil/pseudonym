from pecan import conf
from pecan.jsonify import jsonify
from pymongo import MongoClient, TEXT

import time
import re
import json
import mf2py


# Connect to the database
client = MongoClient(conf.database.url)
db = client.pseudonym
db.domains.create_index([
    ('domain', TEXT),
    ('name', TEXT)
])


class Pseudonym:
    '''
    Base class representing a "pseudonym" for a domain.

    Subclasses simply set a "target" ('twitter', 'instagram')
    property and a "regex" property (a compiled regex which can
    be used to parse out the username on the target).

    There is an `identify_url` classmethod that can be used to
    find the matching pseudonym for a specific URL.
    '''

    registry = {}

    def __init_subclass__(cls, **kw):
        cls.registry[cls.target] = cls

    def __init__(self, url, name, username=None):
        self.url = url
        self.name = name
        self.username = username

    @property
    def matches(self):
        match = self.regex.match(self.url)
        if not match:
            return False

        self.username = match.groups()[1].replace('/', '')

        return True

    @classmethod
    def identify_url(cls, url, name=None):
        for PseudonymCls in cls.registry.values():
            pseudonym = PseudonymCls(url, name)
            if pseudonym.matches:
                return pseudonym

    @property
    def mention_text(self):
        return '@' + self.username

    @property
    def mention_html(self):
        name = self.name or ('@' + self.username)
        return '<a href="' + self.url + '">' + name + '</a>'

    def __json__(self):
        return {
            'url': self.url,
            'username': self.username,
            'name': self.name,
            'target': self.target
        }

    @classmethod
    def from_json(cls, data):
        PseudonymCls = cls.registry[data['target']]
        return PseudonymCls(
            url=data['url'],
            name=data['name'],
            username=data['username']
        )



class TwitterPseudonym(Pseudonym):
    target = 'twitter'
    regex = re.compile(r'^https?\:\/\/(www\.)?twitter.com\/([\S]+\.?)')


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



class Domain:
    '''
    Represents an IndieWeb domain which is properly marked up
    with microformats2, including rel-me links for each pseudonym,
    and a representative h-card (optional) which can be used to
    identify a name for this identity.
    '''

    def __init__(self, domain, fetch=True):
        self.domain = domain
        self.pseudonyms = {}
        self.name = None
        self.timestamp = None

        if fetch:
            self.fetch()

    def fetch(self):
        # fetch the website and parse for microformats
        url = 'http://' + self.domain + '/'
        try:
            parser = mf2py.Parser(url=url)
        except:
            try:
                url = url.replace('http://', 'https://')
                parser = mf2py.Parser(url=url)
            except:
                return None

        # identify the representative h-card and store basic information
        hcards = parser.to_dict(filter_by_type='h-card')
        if len(hcards):
            hcard = hcards[0]
            self.name = hcard['properties'].get('name', [None])[0]

        # identify rel-me links as pseudonyms
        matches = {}
        for url in parser.to_dict()['rels'].get('me', []):
            match = Pseudonym.identify_url(url, self.name)
            if not match:
                continue
            if match.target not in self.pseudonyms:
                self.pseudonyms[match.target] = match

        # remember the last time I fetched
        self.timestamp = time.time()

        # save to the database
        self.save()

    def save(self):
        domain = db.domains.find_one({'domain': self.domain.lower()})
        if domain:
            db.domains.replace_one(
                {'domain': self.domain.lower()},
                jsonify(self)
            )
        else:
            db.domains.insert_one(jsonify(self))

    def __json__(self):
        return {
            'timestamp': self.timestamp,
            'domain': self.domain,
            'name': self.name,
            'pseudonyms': [
                jsonify(p) for p in self.pseudonyms.values()
            ]
        }

    @classmethod
    def from_json(cls, data):
        domain = cls(data['domain'], fetch=False)
        domain.name = data['name']
        domain.timestamp = data['timestamp']
        for pseudonym_data in data['pseudonyms']:
            pseudonym = Pseudonym.from_json(pseudonym_data)
            domain.pseudonyms[pseudonym.target] = pseudonym
        return domain

    @classmethod
    def find_or_fetch(cls, domain):
        regex = re.compile(r'^(?!:\/\/)(?=.{1,255}$)((.{1,63}\.){1,127}(?![0-9]*$)[a-z0-9-]+\.?)$')
        if not regex.match(domain):
            return None

        domain_doc = db.domains.find_one({'domain': domain.lower()})
        if domain_doc:
            if (time.time() - domain_doc['timestamp']) < 100:
                return cls.from_json(domain_doc)
        return cls(domain, fetch=True)

    @classmethod
    def search(cls, term):
        results = db.domains.find({'$text': {'$search': term}})
        return [
            Domain.from_json(domain_doc)
            for domain_doc in results
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

        match = self.regex.search(self.content)
        if not match:
            return versions

        domain = Domain(match.groups()[0])
        for pseudonym in domain.pseudonyms.values():
            versions[pseudonym.target] = {}
            versions[pseudonym.target]['text'] = self.regex.sub(
                pseudonym.mention_text,
                self.content
            )
            versions[pseudonym.target]['html'] = self.regex.sub(
                pseudonym.mention_html,
                self.content
            )

        return versions
