# -*- coding: utf-8 -*-
#
# Quis leget haec?
"""
Tumblor

Tumblor is a library which takes care of collecting oauth credentials
from tumblr all within the confines of the sublime text editor.

It does this primarily by creating a single serving http request handler
and setting that as the callback url that tumblr sees.

Set consumer_key and secret_key in Stumblr.sublime-settings

:copyright: (c) 2013 marcos.a.ojeda <marcos at generic dot cx>
:license: MIT, see LICENSE for details
"""

from __future__ import unicode_literals

import logging
import sys

try:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
except Exception:
    from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import os.path
import sublime
try:
    from Stumblr import requests
    from Stumblr.requests_oauthlib import OAuth1
except ImportError:
    import requests
    from requests_oauthlib import OAuth1
try:
    from urlparse import parse_qs, urlparse
except ImportError:
    from urllib.parse import parse_qs, urlparse
import webbrowser


VERIFIER = None


class TumblrOAuthCallbackHandler(BaseHTTPRequestHandler):
    """A single serving http request handler"""
    def do_GET(self):
        global VERIFIER
        url = urlparse(self.path)
        VERIFIER = url.query
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        def get_bytes(filename):
            rsrc = sublime.find_resources(filename)[0]
            return sublime.load_binary_resource(rsrc)
        if url.query:
            self.wfile.write(get_bytes('stumblr_success.html'))
        else:
            self.wfile.write(get_bytes('stumblr_failure.html'))

        return


class Tumblor(object):
    """some utilities for accessing tumblr"""
    request_token_url = 'https://www.tumblr.com/oauth/request_token'
    authorize_url = 'https://www.tumblr.com/oauth/authorize'
    access_token_url = 'https://www.tumblr.com/oauth/access_token'

    def __init__(self, consumer_key, secret_key, credentials=None,
        base_hostname=None):
        if not consumer_key or not secret_key:
            logging.error('no consumer key/secret passed')
            return

        self.consumer_key = consumer_key
        self.secret_key = secret_key

        if base_hostname:
            self.base_hostname = base_hostname

        if credentials:
            logging.info("got saved credentials and reloading")
            self.oauth_token = credentials['oauth_token']
            self.oauth_token_secret = credentials['oauth_token_secret']

        else:
            # set up rigamarole to do oauth dance
            logging.info("preparing to get oauth credentials")
            # TODO (marcos): collect port from the settings file (or init)
            self.minihttpd = HTTPServer(('0.0.0.0', 8123),
                TumblrOAuthCallbackHandler)
            self.start_auth()
            result = self.get_verifier()
            if result:
                logging.info('getting oauth tokens from init')
                self.get_tokens()

        self.oauth = OAuth1(self.consumer_key,
            client_secret=self.secret_key,
            resource_owner_key=self.oauth_token,
            resource_owner_secret=self.oauth_token_secret)
        return


    def start_auth(self):
        oauth = OAuth1(self.consumer_key,
            client_secret=self.secret_key)
        # TODO move this callback url into some more abstracted settings
        payload = {'oauth_callback':'http://0.0.0.0:8123/stumblrcallback'}
        req = requests.post(url=self.request_token_url, params=payload,
            auth=oauth)
        logging.info('request token content: %s' % req.text)
        creds = parse_qs(req.text)

        logging.info(creds)
        # gather some parsed tokens from the request
        self.oauth_token = creds.get('oauth_token')[0]
        logging.info('oauth_token: %s' % self.oauth_token)
        self.oauth_token_secret = creds.get('oauth_token_secret')[0]
        logging.info('oauth_token_secret: %s' % self.oauth_token_secret)
        return True

    def get_verifier(self):
        global VERIFIER

        # get user auth
        webbrowser.open('%s?oauth_token=%s' % (self.authorize_url,
            self.oauth_token))

        # wait until we push the allow button before killing the server
        while VERIFIER is None:
            self.minihttpd.handle_request()

        # read verifier data handed back via querystring
        data = parse_qs(VERIFIER)
        VERIFIER = None

        logging.info("parsed verifier: %s" % data)
        if 'oauth_verifier' in data:
            self.oauth_verifier = data.get('oauth_verifier')[0]
            logging.info('got verifier: %s', self.oauth_verifier)
            return True
        logging.info('no verifier in response, user probably denied oauth')
        return False

    def get_tokens(self):
        oauth = OAuth1(self.consumer_key,
            client_secret=self.secret_key,
            resource_owner_key=self.oauth_token,
            resource_owner_secret=self.oauth_token_secret,
            verifier=self.oauth_verifier)
        req = requests.post(url=self.access_token_url, auth=oauth)
        logging.info("access token content: %s" % req.text)
        creds = parse_qs(req.text)

        logging.info("getting long-lasting access tokens")
        self.oauth_token = creds.get('oauth_token')[0]
        logging.info('oauth_token: %s' % self.oauth_token)
        self.oauth_token_secret = creds.get('oauth_token_secret')[0]
        logging.info('oauth_token_secret: %s' % self.oauth_token_secret)

    def serialize_credentials(self):
        bundle = None
        if self.oauth_token and self.oauth_token_secret:
            bundle = {
                'oauth_token': self.oauth_token,
                'oauth_token_secret': self.oauth_token_secret
            }
        return bundle

    def call_api(self, method=None, params={}, type='blog', verb='get'):
        """A simple abstraction for calling the tumblr api"""
        if method:
            endpoint = ('https://api.tumblr.com/v2/blog/%s%s'
                % (self.base_hostname, method))
            if verb == 'post':
                req = requests.post(url=endpoint, data=params, auth=self.oauth)
            else:
                req = requests.get(url=endpoint, params=params, auth=self.oauth)
            return req.json()
        return None
