Pseudonym
=========

Pseudonym is a simple web service API designed to help
[IndieWeb](https://www.indieweb.org) websites with the problem of "mentioning"
people both on the IndieWeb and on [silos](https://indieweb.org/silo). A version
of this code is available as a service at
[https://pseudonym.cleverdevil.io](https://pseudonym.cleverdevil.io).

For example, on the IndieWeb, my identity is [my
website](https://cleverdevil.io), which is published at
[https://cleverdevil.io]. I am also present on a number of silos, including:

* [@cleverdevil on Micro.blog](http://micro.blog/cleverdevil)
* [@cleverdevil on Twitter](https://twitter.com/cleverdevil)
* [@cleverdevil on LinkedIn](https://www.linkedin.com/in/cleverdevil)
* [@cleverdevil on GitHub](https://github.com/cleverdevil)
* Etc.

While I have been lucky enough to get the same "nickname" across all of these
silos, not all people have been so lucky. When attempting to syndicate a post
from my website to other services such as Twitter and Micro.blog while
"mentioning" someone else, I may need to format that "mention" in a different
way per service, perhaps even with a different username. Pseudonym aims to make
this a bit simpler. How? Well, let's dive into the API.

Pseudonym Lookup
----------------

To determine the "pseudonyms" for a particular IndieWeb identity, simply send an
`HTTP GET` request to `https://pseudonym.cleverdevil.io/identity?url=` with an
IndieWeb website passed in as the `url` parameter. For example:

```
http get https://pseudonym.cleverdevil.io/identity?url=https://cleverdevil.io

{
    "name": "Jonathan LaCour",
    "nicknames": null,
    "pseudonyms": [
        {
            "target": "twitter",
            "url": "https://twitter.com/cleverdevil",
            "username": "cleverdevil"
        },
        {
            "target": "linkedin",
            "url": "https://www.linkedin.com/in/cleverdevil",
            "username": "cleverdevil"
        },
        {
            "target": "keybase",
            "url": "https://keybase.io/cleverdevil",
            "username": "cleverdevil"
        },
        {
            "target": "github",
            "url": "https://github.com/cleverdevil",
            "username": "cleverdevil"
        },
        {
            "target": "instagram",
            "url": "https://instagram.com/cleverdevil",
            "username": "cleverdevil"
        },
        {
            "target": "micro.blog",
            "url": "https://micro.blog/cleverdevil",
            "username": "cleverdevil"
        }
    ],
    "timestamp": 1549327619.68206,
    "url": "https://cleverdevil.io/"
}
```

The requested URL will be fetched and parsed. The "name" and "nicknames" from
the website's [h-card](https://indieweb.org/h-card) will be identified, along
with any "pseudonyms" declared as [rel-me](https://indieweb.org/rel-me)
references.

Individual identities will be cached in Pseudonym, and will be updated on-demand
at most once every 24 hours.

Identity Search
---------------

Interested in finding an identity based upon their username on a silo or a
`p-nickname` or `p-name` declared in their `h-card`? You can search the cache
that Pseudonym is aware of by sending an `HTTP GET` request:

```
http get https://pseudonym.cleverdevil.io/search?term=lacour

[
    {
        "name": "Jonathan LaCour",
        "nicknames": null,
        "pseudonyms": [
            {
                "target": "twitter",
                "url": "https://twitter.com/cleverdevil",
                "username": "cleverdevil"
            },
            {
                "target": "linkedin",
                "url": "https://www.linkedin.com/in/cleverdevil",
                "username": "cleverdevil"
            },
            {
                "target": "keybase",
                "url": "https://keybase.io/cleverdevil",
                "username": "cleverdevil"
            },
            {
                "target": "github",
                "url": "https://github.com/cleverdevil",
                "username": "cleverdevil"
            },
            {
                "target": "instagram",
                "url": "https://instagram.com/cleverdevil",
                "username": "cleverdevil"
            },
            {
                "target": "micro.blog",
                "url": "https://micro.blog/cleverdevil",
                "username": "cleverdevil"
            }
        ],
        "timestamp": 1549327619.68206,
        "url": "https://cleverdevil.io/"
    }
]
```

A list of matched identities will be returned.

Content Formatting
------------------

If you'd like some help formatting your content for syndication, you can
leverage Pseudonym to transform your content automatically for different
syndication targets. Simply use Pseudonym's special "@{}" mention syntax. If you
want to "mention" me, you would use `@{https://cleverdevil.io}` or
`@{cleverdevil.io}` for short in your post. Then, send that content to Pseudonym
via an `HTTP POST`:

```
http post https://pseudonym.cleverdevil.io/format content="Hello @{cleverdevil.io}, I hope you're well."

{
    "github": {
        "html": "Hello <a href=\"https://github.com/cleverdevil\">Jonathan LaCour</a>, I hope you're well..",
        "text": "Hello @cleverdevil, I hope you're well.."
    },
    "instagram": {
        "html": "Hello <a href=\"https://instagram.com/cleverdevil\">Jonathan LaCour</a>, I hope you're well..",
        "text": "Hello @cleverdevil, I hope you're well.."
    },
    "keybase": {
        "html": "Hello <a href=\"https://keybase.io/cleverdevil\">Jonathan LaCour</a>, I hope you're well..",
        "text": "Hello @cleverdevil, I hope you're well.."
    },
    "linkedin": {
        "html": "Hello <a href=\"https://www.linkedin.com/in/cleverdevil\">Jonathan LaCour</a>, I hope you're well..",
        "text": "Hello @cleverdevil, I hope you're well.."
    },
    "micro.blog": {
        "html": "Hello <a href=\"https://micro.blog/cleverdevil\">Jonathan LaCour</a>, I hope you're well..",
        "text": "Hello @cleverdevil, I hope you're well.."
    },
    "original": {
        "html": "Hello @{cleverdevil.io}, I hope you're well..",
        "text": "Hello @{cleverdevil.io}, I hope you're well.."
    },
    "twitter": {
        "html": "Hello <a href=\"https://twitter.com/cleverdevil\">Jonathan LaCour</a>, I hope you're well..",
        "text": "Hello @cleverdevil, I hope you're well.."
    }
}
```

Multiple `@{}` mentions are allowed for a single request, but be aware that in
some cases a particular identity may not be present in a particular target.
