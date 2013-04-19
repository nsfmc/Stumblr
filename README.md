# Stumblr

a sublime text 3 interface to tumblr

*n.b. this is super rough. i have been using it happily for about two weeks now, ironing out kinks, but, naturally, caveat emptor.*

## Installing

for now, because this is all very early stage, your best bet is to

    cd '~/Library/Application Support/Sublime Text 3/Packages'
    git clone https://github.com/nsfmc/Stumblr

After you clone, though, you need to go to...

http://www.tumblr.com/oauth/apps

and create a new app. Once you have a consumer key and secret key from tumblr, you can feed those into the User settings.

## Step By Step Setup

1 When registering your app, for callback url, you should put something like `http://example.com/my/callback` this will actually *never* get hit (but it should point to a real domain of yours to be polite) because the plugin will receive the callback itself (similar to how mobile apps do it)

2. from there, you **need** to update the user settings

![stumblr user settings](http://dl.dropbox.com/u/406291/Screenshots/oef7.png)

3. The next step is to actually login. Hit `Super-Shift-P` and type `login`, select *Stumblr: Login* This will start an oauth party going, so you never have to store your password anywhere.

![stumblr login](http://dl.dropbox.com/u/406291/Screenshots/Bvpo.png)

4. This should open a web browser window that should look like this:

![stumblr oauth verify](http://dl.dropbox.com/u/406291/Screenshots/wBUz.png)

5. If you hit yes, you'll see a confirmation window. You can leave it open, or close it.

![stumblr oauth confirmation](http://dl.dropbox.com/u/406291/Screenshots/CqPw.png)

6. Now, you can start editing drafts like a pro! Again, hitting `Super-Shift-P`, you can now type `fetch` and select *Stumblr: Fetch Drafts*

![stumblr fetch drafts](http://dl.dropbox.com/u/406291/Screenshots/70PO.png)

7. This will populate the quick list with any drafts you've been meaning to finish up, like so:

![a draft list](http://dl.dropbox.com/u/406291/Screenshots/oOYe.png)

8. When you select one, one or two buffers will be created for the given post you've selected. Each time you hit save, the buffer you were editing will be updated remotely on tumblr. These buffers are temporary files and will be deleted them when you close them if they're saved.

Try it out a few times and see if it does what you expect. The filenames include the relevant field, so for quotes, you should see a tab for 'source' and another for 'text'. Each time you save, the status bar will update with the status of the given save. If you don't see a success, you will probably want to save-as.

![draft buffers](https://dl.dropboxusercontent.com/u/406291/Screenshots/sJE6.png)

if you decide you want to publish a given post, you can call up the menu and type 'publish.'

## Other commands

You can start a draft on stumblr by posting the current buffer. The command is *Stumblr: Post as Draft.*

You can also delete a draft via *Stumblr: Delete Current Draft*

If you don't like the idea of using the auto-save functionality, you can alternatively update a post manually. The command is *Stumblr: Update Current Draft* and will only appear on drafts that were gathered using the Fetch command.

You can copy over the default settings from the adjacent `Settings - Default` menu item to get you started, but all the comments will go away once you login.

## The default settings

```json
{
    // these will be the 'OAuth Consumer Key' and 'secret key' you'll
    // get from http://www.tumblr.com/oauth/apps
    // THESE ARE NOT ACTUAL KEYS, you need to get them at that url above
    // but when you actually get them, they will look suspiciously like this
    // "consumer_key": "P4w7ibTrFa1VzBUp4PqCwE9uOTc7uvc6IlfjpYqCleiJmA60YE6",
    // "secret_key": "BiXIvB0BZdyGD2E7ich9TArASZEjzAFGiMzE3qdnWznW3Vw54o",

    // this should be the base hostname or cname of the blog you are posting to
    // "base_hostname": "nsfmc.tumblr.com",

    // these should either be acquired manually (hardcore!) or you should use
    // the Stumblr: login command to commence the oauth tango for you.
    // THESE ARE NOT ACTUAL TOKENS, you should override these by either, again
    // running the 'Stumblr: login' command or by manually acquiring oauth tokens
    // "oauth_token": "PoqWHfHpxYfbaa9zgR9TZoNW43lfTojWb1BpdWSoGLCSRc79El",
    // "oauth_token_secret": "dPFJVImpqULgpqRfiYtchMvPJY6cDqdG0UFKmpRvZgCZJearC2",

    // the default setting, true, automatically updates a post's buffer on save.
    // This is probably what you want since the default action is to edit drafts
    // and not published posts.
    "update_on_save": true,

    // the port that the initial oauth callback listens on. This should be an
    // unoccupied port on the local computer, so don't set it to anything that
    // will already be bound or the tumblor requesthandler will break.
    // TODO(marcos): enable this correctly, this is connected to nothing right now
    "callback_port": 8123
}
```

## Finally

I hope this is useful to you, please let me know, marcos at generic dot cx. Pull requests welcome, this is clearly my first time hacking away at a sublime text plugin.
