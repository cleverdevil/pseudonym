from pecan import expose, redirect, response, request, abort

from ..lib import Domain, Content, Pseudonym


class DomainController:

    def __init__(self, domain):
        self.domain = Domain.find_or_fetch(domain)
        if self.domain is None:
            abort(404)

    @expose('json')
    def all(self):
        return self.domain

    @expose('json')
    def _default(self, target):
        if target.lower() in self.domain.pseudonyms:
            return self.domain.pseudonyms[target.lower()]
        abort(404)


class DomainsController:

    @expose()
    def _lookup(self, domain, *remainder):
        return DomainController(domain), remainder


class ContentController:

    @expose('json')
    def format(self, content=''):
       return Content(content).transform()


class SearchController:

    @expose('json')
    def _default(self, term):
        return Domain.search(term)


class RootController:
    domains = DomainsController()
    content = ContentController()
    search = SearchController()
