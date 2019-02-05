from pecan import expose, redirect, response, request, abort

from ..lib import Identity, Content, Pseudonym


class RootController:
    @expose('json')
    def identity(self, url, force=False):
        identity = Identity.find_or_fetch(url, force=force)
        if identity is None:
            abort(404)

        return identity

    @expose('json')
    def format(self, content=''):
        return Content(content).transform()

    @expose('json')
    def search(self, term):
        return Identity.search(term)
