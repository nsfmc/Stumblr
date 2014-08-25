# -*- coding: utf-8 -*-
#
# Quis leget haec?
"""
Stumblr

Stumblr is a Sublime Text 3 interface to tumblr

:copyright: (c) 2013 marcos.a.ojeda <marcos at generic dot cx>
:license: MIT, see LICENSE for details
"""

import json
import logging
import os
import os.path
import re

# this happens to let tumblor correctly load requests and requests_oauth
# without incident, but it's not 100% ideal :(
import sys
sys.path.append(os.path.dirname(__file__))

try:
    import Stumblr.tumblor as tumblor
except ImportError:
    import tumblor
from lib.thread_progress import ThreadProgress
import sublime
import sublime_plugin
import tempfile
import threading
try:
    from urlparse import parse_qs, urlparse
except ImportError:
    from urllib.parse import parse_qs, urlparse
import webbrowser

logging.basicConfig(level=logging.DEBUG,
    format='%(levelname)s\t%(asctime)s [%(filename)s:%(lineno)d] %(message)s')

PREFSFILE = 'Stumblr.sublime-settings'

class TumblrUtility(object):
    def __init__(self):
        self.prefsfile = 'Stumblr.sublime-settings'
        self.prefs = sublime.load_settings(self.prefsfile)
        self.t = self.get_tumblr()

    @property
    def application_tokens(self):
        return (self.prefs.get('consumer_key', '') and
            self.prefs.get('secret_key', ''))

    @property
    def oauth_tokens(self):
        """returns the oauth token and oauth token secret"""
        prefs = self.prefs
        if (not prefs.get('oauth_token') or
            not prefs.get('oauth_token_secret')):
            return None
        return {
            'oauth_token': prefs.get('oauth_token'),
            'oauth_token_secret': prefs.get('oauth_token_secret')
        }

    def get_tumblr(self):
        """returns an authenticated tumblor instance ready to call"""
        creds = self.oauth_tokens
        prefs = self.prefs
        if not creds:
            logging.debug('no creds!')
            return None
        logging.debug('returning Tumblor')
        return tumblor.Tumblor(prefs.get('consumer_key'),
            prefs.get('secret_key'), credentials=creds,
            base_hostname=prefs.get('base_hostname'))

    def get_new_tokens(self):
        prefs = self.prefs
        sublime.status_message('[STUMBLR] Starting OAuth Dance')
        t = tumblor.Tumblor(prefs.get('consumer_key'), prefs.get('secret_key'),
            credentials=None, base_hostname=prefs.get('base_hostname'))
        tokens = t.serialize_credentials()
        prefs.set('oauth_token', tokens['oauth_token'])
        prefs.set('oauth_token_secret', tokens['oauth_token_secret'])
        sublime.save_settings(PREFSFILE)
        return tokens


class CheckCredentialsCommand(sublime_plugin.WindowCommand):
    """Checks to see if user has gathered oauth tokens yet"""
    def run(self):
        tum = TumblrUtility()
        if not tum.application_tokens:
            sublime.status_message('[STUMBLR] Set application keys in %s' % PREFSFILE)
            return

        if tum.oauth_tokens:
            sublime.status_message('[STUMBLR] Already logged in')
            return

        sublime.status_message('[STUMBLR] Run tumblr login')
        return


class TumblrListDraftsCommand(sublime_plugin.WindowCommand):
    """Lists your tumblr drafts in the quick panel"""
    def run(self):
        draft_thread = ListDraftsThreaded(self.window)
        draft_thread.start()
        ThreadProgress(draft_thread, 'Fetching Drafts', '')


class ListDraftsThreaded(threading.Thread, TumblrUtility):
    """Fetches tumblr drafts for display in quick panel"""
    def __init__(self, window):
        self.window = window
        self.drafts = None
        self.strip_tags_re = re.compile(r'<[^>]*>?')
        threading.Thread.__init__(self)
        TumblrUtility.__init__(self)

    def run(self):
        posts = self.get_draft_list()
        logging.info("loaded %s posts" % len(posts))
        def show_panel():
            self.window.show_quick_panel(self.draft_list, self.on_done)

        if len(posts):
            sublime.set_timeout(show_panel, 10)
        sublime.status_message('[STUMBLR]: No drafts. Get writing!')

    def get_draft_list(self):
        drafts = self.t.call_api('/posts/draft', params={'filter':'raw'})
        if drafts['meta']['status'] == 200:
            self.drafts = drafts['response']['posts']
            if len(self.drafts):
                self.draft_list = [self.snippet(p) for p in self.drafts]
                return self.drafts
            logging.info('no drafts found')
            return []
        logging.error('[STUMBLR]: Request for drafts failed.')
        logging.error(drafts)
        return []

    def snippet(self, post):
        """summarizes various kinds of posts for display in quick menu
        """
        if post['type'] == 'text':
            return [post['title'][:60] or post['slug'][:60],
                post['date'],
                self.strip_tags(post['body'])[:80]
            ]
        if post['type'] == 'quote':
            source = self.strip_tags(post.get('source', ''))
            if(post.get('source_url')):
                source = urlparse(post.get('source_url','')).path
            source_title = post.get('source_title', '')
            return [source[-60:],
                "%s: %s" % (post['date'], source_title),
                self.strip_tags(post['text'])[:80]
            ]
        if post['type'] == 'link':
            source = urlparse(post['url']).netloc
            return [post['title'][:60],
                "%s: %s" % (post['date'], source),
                self.strip_tags(post['description'])[:80]
            ]
        if post['type'] == 'photo':
            return [post['slug'][:60],
                post['date'],
                post['caption'][:80]
            ]
        else:
            return [post['slug'], post['date'], ""]

    def strip_tags(self, markup):
        if markup:
            return self.strip_tags_re.sub('', markup)
        return ""

    def on_done(self, index):
        if index == -1:
            logging.info("canceled out of fetch draft quick list")
        else:
            logging.info("picked draft:\n\n %s " % self.drafts[index])
            self.new_buffer_from_post(self.drafts[index])
        return

    def new_buffer_from_post(self, post):
        mapping = {
            'text': ['title', 'body'],
            'photo': ['caption'],
            'quote': ['source', 'text'],
            'link': ['title', 'description'],
            'chat': ['title', 'conversation']
        }
        fields = mapping[post['type']]
        for field in fields:
            self.new_view_with_text(post[field], {
                'id': str(post['id']),
                'field': field
            })

    def new_view_with_text(self, text, settings={}):
        """creates a new view and fills it with text"""
        temp, tempname = tempfile.mkstemp(prefix='stumblr_%s_'%settings['field'])
        logging.debug('have fd: %s, path: %s' % (temp, tempname))
        temp = os.fdopen(temp, 'wb')
        temp.write(text.encode('utf-8'))
        temp.close()

        new_view = self.window.open_file(tempname)
        new_view.settings().set('stumblr_post', True)
        for k in settings:
            logging.debug('setting %s:%s for view' % (k, settings[k]))
            new_view.settings().set('stumblr_%s' % k, settings[k])
            self.set_syntax(new_view)
        pass

    def set_syntax(self, view):
        """looks for a markdown syntax and applies it to a view"""
        possible_syntaxes = sublime.find_resources("Markdown.tmLanguage")
        if possible_syntaxes:
            md_syntax = possible_syntaxes[0]
            logging.debug('setting syntax file to: %s', md_syntax)
            view.set_syntax_file(md_syntax)
        else:
            logging.debug('could not finde a Markdown.tmLanguage')
        return None


class StumblrEvents(sublime_plugin.EventListener):
    """deletes stumblr posts when closed"""
    def on_close(self, view):
        view_prefs = view.settings()
        if view_prefs.get('stumblr_post'):
            original_name = view.file_name()
            if original_name and os.path.exists(original_name):
                logging.info("unlinking: %s" % original_name)
                os.remove(original_name)
            pass
        return

    def on_pre_save(self, view):
        """posts the draft to tumblr when saving a dirty buffer"""
        master_prefs = sublime.load_settings(PREFSFILE)
        if not master_prefs.get('update_on_save'):
            return

        view_prefs = view.settings()
        if view_prefs.get('stumblr_post') and view.is_dirty():
            logging.debug('Stumblr: trying to post draft')
            postup = UpdateDraftThreaded(view)
            postup.start()
            ThreadProgress(postup, 'Updating draft on tumblr',
                '[STUMBLR] Draft Posted successfully!',
                '[STUMBLR] Draft Post failed')
            return
        return


class TumblrUpdateDraftCommand(sublime_plugin.TextCommand):
    """Manually update a draft if update-on-save thing is not for you"""
    def run(self, edit):
        view_prefs = self.view.settings()
        if view_prefs.get('stumblr_post'):
            postup = UpdateDraftThreaded(self.view)
            postup.start()
            ThreadProgress(postup, 'Updating draft on tumblr',
                '[STUMBLR] Draft Updated successfully!',
                '[STUMBLR] Draft Update failed')
            return

    def is_enabled(self):
        if self.view.settings().get('stumblr_post'):
            return True
        return False


class UpdateDraftThreaded(threading.Thread, TumblrUtility):
    """A threaded """
    def __init__(self, view):
        self.view = view
        view_prefs = view.settings()
        self.post_id = int(view_prefs.get('stumblr_id'))
        self.post_field = view_prefs.get('stumblr_field')
        threading.Thread.__init__(self)
        TumblrUtility.__init__(self)

    def run(self):
        sublime.set_timeout(self.post_view, 10)

    def post_view(self):
        body = self.view.substr(sublime.Region(0, self.view.size()))
        logging.info("saving post: %s@%s" % (self.post_id, self.post_field))
        params = {
            'id': self.post_id,
            self.post_field: body
        }
        logging.info(params)
        result = self.t.call_api('/post/edit', verb='post', params=params)
        logging.info(result)
        if result['meta']['status'] == 200:
            sublime.status_message('[STUMBLR] draft updated successfully')
        else:
            logging.error("Update Post failed with result: %s" % result)
            sublime.status_message('[STUMBLR] there was an error updating the draft')
        return


class TumblrLoginCommand(sublime_plugin.WindowCommand):
    """
    Logs a user into tumblr, with nonblocking magic
    """

    def run(self):
        TumblrThreadedLogin(self.window).start()


class TumblrThreadedLogin(threading.Thread, TumblrUtility):

    def __init__(self, window):
        self.window = window
        threading.Thread.__init__(self)
        TumblrUtility.__init__(self)

    def run(self):
        self.get_new_tokens()

        def show_status():
            if self.oauth_tokens:
                sublime.status_message('[STUMBLR] Logged in successfully!')
            else:
                sublime.status_message('[STUMBLR] Login failed')
            return

        sublime.set_timeout(show_status, 10)


class TumblrPublishDraftCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        TumblrThreadedPublishDraft(self.view).start()

    def is_enabled(self):
        if self.view.settings().get('stumblr_post'):
            return True
        return False


class TumblrThreadedPublishDraft(threading.Thread, TumblrUtility):
    def __init__(self, view):
        self.view = view
        self.view_settings = view.settings()
        self.post_id = int(self.view_settings.get('stumblr_id'))
        threading.Thread.__init__(self)
        TumblrUtility.__init__(self)

    def run(self):
        def publish_post():
            info = self.t.call_api(method='/post/edit', params={
                'id': self.post_id,
                'state': 'published',
            }, verb='post')
            logging.debug(info)
            # TODO(marcos): what if the post fails? maybe set the status message?
            if info['meta']['status'] == 200:
                published_id = info['response']['id']
                more_info = self.t.call_api(method='/posts', params={
                    'api_key': self.prefs.get('consumer_key'),
                    'id': published_id
                })
                logging.debug(more_info)
                # TODO(marcos): what if this also fails?
                if more_info['meta']['status'] == 200:
                    post = more_info['response']['posts'][0]
                    # TODO(marcos): maybe check a pref for this
                    webbrowser.open(post['post_url'])

        sublime.set_timeout(publish_post, 10)


class TumblrPostDraftCommand(sublime_plugin.TextCommand):
    """
    Posts the current view to tumblr as a draft
    """
    def run(self, edit):
        TumblrThreadedPostDraft(self.view).start()


class TumblrThreadedPostDraft(threading.Thread, TumblrUtility):
    """
    Posts a view to tumblr
    """
    def __init__(self, view):
        self.view = view
        self.response = None
        threading.Thread.__init__(self)
        TumblrUtility.__init__(self)

    def run(self):

        def show_status():
            self.post_draft()
            logging.info(self.response)
            if self.response['meta']['status'] == 201:
                sublime.status_message('[STUMBLR] Draft Posted successfully!')
                self.view.set_name(str(self.response['response']['id']))
                prefs = self.view.settings()
                prefs.set('stumblr_post', True)
                prefs.set('stumblr_id', str(self.response['response']['id']))
                prefs.set('stumblr_field', 'body')
            else:
                sublime.status_message('[STUMBLR] Draft Post failed')
                # clearing this prevents the underlying file being killed when
                # the view gets closed
                prefs.erase('stumblr_post')
            return

        sublime.set_timeout(show_status, 10)

    def post_draft(self):
        if self.t:
            body = self.view.substr(sublime.Region(0, self.view.size()))
            payload = {
                'state':'draft', 'type':'text', 'format':'markdown',
                'body':body
            }
            self.response = self.t.call_api('/post', params=payload, verb='post')


class TumblrDeleteDraftCommand(sublime_plugin.TextCommand):
    """Deletes the current buffer's associated post on tumblr"""
    def run(self, edit):
        TumblrThreadedDeleteDraftCommand(self.view).start()

    def is_enabled(self):
        if self.view.settings().get('stumblr_post'):
            return True
        return False



class TumblrThreadedDeleteDraftCommand(threading.Thread, TumblrUtility):
    """
    Deletes a view on tumblr, but provides a dialog before actually doing it
    """
    def __init__(self, view):
        self.view = view
        self.response = None
        self.view_settings = view.settings()
        self.post_id = int(self.view_settings.get('stumblr_id'))
        threading.Thread.__init__(self)
        TumblrUtility.__init__(self)

    def run(self):
        def delete_draft():
            post = self.t.call_api(method='/posts', params={
                'api_key': self.prefs.get('consumer_key'),
                'id': self.post_id
            })
            logging.debug(post)
            # does the post exist?
            if post['meta']['status'] == 200:
                deleted_post = self.t.call_api(method='/post/delete', params={
                    'id': self.post_id
                }, verb='post')
                logging.debug(deleted_post)
                if deleted_post['meta']['status'] == 200:
                    sublime.status_message('[STUMBLR] Post #%s Deleted' % self.post_id)
                    return
            sublime.status_message('[STUMBLR] Failed on Deleting Post #%s' % self.post_id)
            return

        sublime.set_timeout(delete_draft, 10)
