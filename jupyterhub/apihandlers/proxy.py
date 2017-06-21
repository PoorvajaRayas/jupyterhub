"""Proxy handlers"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json
from urllib.parse import urlparse

from tornado import gen, web

from .. import orm
from ..proxy import RouteSpec
from ..utils import admin_only
from .base import APIHandler

class _RouteSpecJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles routespecs"""
    def encode(self, obj):
        if isinstance(obj, RouteSpec):
            obj = obj.host + obj.path
        return super().encode(obj)

    def iterencode(self, obj, _one_shot=True):
        if isinstance(obj, dict):
            obj = {
                key.host + key.path if isinstance(key, RouteSpec) else key : value
                for key, value in obj.items()
            }
        return super().iterencode(obj)

_json = _RouteSpecJSONEncoder()

class ProxyAPIHandler(APIHandler):
    
    @admin_only
    @gen.coroutine
    def get(self):
        """GET /api/proxy fetches the routing table

        This is the same as fetching the routing table directly from the proxy,
        but without clients needing to maintain separate
        """
        routes = yield self.proxy.get_all_routes()
        self.write(_json.encode(routes))

    @admin_only
    @gen.coroutine
    def post(self):
        """POST checks the proxy to ensure that it's up to date.

        Can be used to jumpstart a newly launched proxy
        without waiting for the check_routes interval.
        """
        yield self.proxy.check_routes(self.users, self.services)
    
    @admin_only
    @gen.coroutine
    def patch(self):
        """PATCH updates the location of the proxy
        
        Can be used to notify the Hub that a new proxy is in charge
        """
        if not self.request.body:
            raise web.HTTPError(400, "need JSON body")
        
        try:
            model = json.loads(self.request.body.decode('utf8', 'replace'))
        except ValueError:
            raise web.HTTPError(400, "Request body must be JSON dict")
        if not isinstance(model, dict):
            raise web.HTTPError(400, "Request body must be JSON dict")
        
        if 'api_url' in model:
            self.proxy.api_url = model['api_url']
        if 'auth_token' in model:
            self.proxy.auth_token = model['auth_token']
        self.log.info("Updated proxy at %s", self.proxy)
        yield self.proxy.check_routes(self.users, self.services)
        


default_handlers = [
    (r"/api/proxy", ProxyAPIHandler),
]
