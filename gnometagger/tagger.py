# This file is a part of Fedora gnome-tagger
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301  USA
#
# Refer to the README.rst and LICENSE files for full details of the license
# -*- coding: utf-8 -*-

'''
main gnome-tagger file.
'''

import argparse
import json
import logging
import urllib2
import os
import requests
import sys

from requests.exceptions import RequestException

from gi.repository import Pango
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import WebKit

__version__ = '0.1.0'

TAGGERAPI = 'https://apps.fedoraproject.org/tagger/api/v1/'
logging.basicConfig()
LOG = logging.getLogger('gnometagger')
FOLDER = os.path.dirname(__file__)

def error_box(window, message_format):
        messagedialog = Gtk.MessageDialog(
            parent=window,
            flags=Gtk.DialogFlags.MODAL,
            type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            message_format=message_format)
        messagedialog.connect("response", widget_close)
        messagedialog.show()


def widget_close(widget, response_id):
    """ Close the widget whatever the action is. """
    widget.destroy()


class GnomeTaggerWindow(Gtk.ApplicationWindow):

    def __init__(self, app):
        window = Gtk.Window.__init__(self, title='GNOME Tagger',
                                     application=app)

        self.debug = app.debug
        self.pkgname = None
        self.statistics = None
        self.user = None

        #self.set_default_size(400, 200)

        grid = Gtk.Grid()
        self.add(grid)
        grid.show()

        # a builder to add the UI designed with Glade to the grid:
        self.builder = Gtk.Builder()
        # get the file (if it is there)
        try:
            self.builder.add_from_file('%s/data/tagger.ui' % FOLDER)
        except:
            print 'file not found'
            sys.exit()
        # and attach it to the grid
        grid.attach(self.builder.get_object('vbox1'), 0, 0, 1, 1)

        # menu option 'statistics'
        stats_action = Gio.SimpleAction.new('statistics', None)
        stats_action.connect('activate', self.stats_action)
        app.add_action(stats_action)

        # menu option 'about'
        about_action = Gio.SimpleAction.new('about', None)
        about_action.connect('activate', self.about_action)
        app.add_action(about_action)

        # search box
        entry_search = self.builder.get_object('entry_search')
        entry_search.connect("activate", self.search_action)
        entry_search.connect("icon-release", self.search_icon_action)

        # show icons on the button
        settings = Gtk.Settings.get_default()
        settings.props.gtk_button_images = True

        # set the window logo
        self.set_icon_from_file('%s/data/tagger.png' % FOLDER)

        # add icon to the Scores button
        scorebutton = self.builder.get_object('button_scores')
        image = Gtk.Image()
        image.set_from_stock(Gtk.STOCK_ABOUT, Gtk.IconSize.BUTTON)
        scorebutton.set_image(image)

        # like/dislike button to vote on tags
        like_icon = GdkPixbuf.Pixbuf.new_from_file_at_size(
            '%s/data/like.png' % FOLDER, 25, 25)
        dislike_icon = GdkPixbuf.Pixbuf.new_from_file_at_size(
            '%s/data/dislike.png' % FOLDER,  25, 25)

        image = Gtk.Image()
        image.set_from_pixbuf(like_icon)
        image.show()
        likebutton = self.builder.get_object('button_like')
        likebutton.add(image)

        image = Gtk.Image()
        image.set_from_pixbuf(dislike_icon)
        image.show()
        dislikebutton = self.builder.get_object('button_dislike')
        dislikebutton.add(image)

        treeview = self.builder.get_object('treeview1')
        treeselection = treeview.get_selection()
        treeselection.set_mode(Gtk.SelectionMode.MULTIPLE)

        cell_tag = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn('Tags')
        column_text.pack_start(cell_tag, True)
        column_text.set_attributes(cell_tag, text=0)
        treeview.append_column(column_text)

        dic = {
            'on_button_next_pkg_clicked': self.next_pkg_action,
            'on_button_add_tag_clicked': self.add_tag_action,
            'on_button_like_clicked': self.like_action,
            'on_button_dislike_clicked': self.dislike_action,
            'on_button_scores_clicked': self.scores_action,
        }
        self.builder.connect_signals(dic)

        self.get_package('firefox')

    @property
    def auth(self):
        """ Return the correct dictionnary to use with the
        authentification header of requests using the self.user
        information.
        """
        return (self.user['name'], self.user['token'])

    def set_messsage(self, message, msgtype='info'):
        """ Set a message into the information label. """
        msg = self.builder.get_object('label_msg')
        if msgtype == 'info':
            msg.set_markup('<span foreground="green">%s</span>' % message)
        elif msgtype == 'error':
            msg.set_markup('<span foreground="red">%s</span>' % message)

    def next_pkg_action(self, *args, **kw):
        """ Retrieve information about the next (random) package and update
        the GUI accordingly.
        """
        LOG.info('next_pkg_action')
        self.set_messsage('')
        self.get_package()

    def add_tag_action(self, *args, **kw):
        """ Retrieve the tags from `entry_tag` and send them to the server,
        update the GUI afterward.
        """
        LOG.info('add_tag_action')

        if not self.user:
            self.get_user_info(self.add_tag_action)
            return

        cursor = Gdk.Cursor(Gdk.CursorType.WATCH)
        self.get_root_window().set_cursor(cursor)
        Gdk.flush()

        self.set_messsage('')
        tagfield = self.builder.get_object('entry_tag')
        entries = tagfield.get_text()
        entries = [entry.strip() for entry in entries.split(',')]
        tagfield.set_text('')
        if entries != ['']:
            data = {'pkgname': self.pkgname, 'tag': ','.join(entries)}
            req = requests.put('%s/tag/%s/' % (TAGGERAPI,
                               self.pkgname),
                               data=data, auth=self.auth,
                               verify=not self.debug)
            LOG.info('output: {0}'.format(req.text))
            jsonreq = json.loads(req.text)
            if req.status_code != 200:
                self.set_messsage(jsonreq['error'], msgtype='error')
                msg.set_text()
            else:
                self.set_messsage('\n'.join(jsonreq['messages']))
            self.get_package(self.pkgname)
        else:
            self.set_messsage('No tag(s) to add', msgtype='error')
            cursor = Gdk.Cursor(Gdk.CursorType.ARROW)
            self.get_root_window().set_cursor(cursor)
            Gdk.flush()

    def like_action(self, *args, **kw):
        """ Retrieve the list of tags which are selected and send to the
        server that they have been 'licked'.
        If no tags are selected show an error dialog.
        """
        LOG.info('like_click')
        self.vote(1)

    def vote(self, vote):
        """ Vote on the selected tag either positively or negatively
        according to the specified vote.
        """

        if not self.user:
            if vote == 1:
                self.get_user_info(self.like_action)
            else:
                self.get_user_info(self.dislike_action)
            return

        self.set_messsage('')
        data = {'pkgname': self.pkgname, 'vote': vote}
        treeview = self.builder.get_object('treeview1')
        selection = treeview.get_selection()
        tree_model, rows = selection.get_selected_rows()
        if not rows:
            self.set_messsage('No tag(s) selected', msgtype='error')
            return
        for tree_iter in rows:
            if tree_iter:
                tag = tree_model[tree_iter][0]
                data['tag'] = tag
                req = requests.put('%s/vote/%s/' % (TAGGERAPI,
                                   self.pkgname),
                                   data=data, auth=self.auth,
                                   verify=not self.debug)
                jsonreq = json.loads(req.text)
                if req.status_code != 200:
                    self.set_messsage(jsonreq['error'], msgtype='error')
                else:
                    self.set_messsage('\n'.join(jsonreq['messages']))

    def dislike_action(self, *args, **kw):
        """ Retrieve the list of tags which are selected and send to the
        server that they have been 'dislicked'.
        If no tags are selected show an error dialog.
        """
        LOG.info('dislike_click')
        self.vote(-1)

    def stats_action(self, *args, **kw):
        """ Retrieves statistics from the server and display them in a
        new dialog.
        These statistics include general statistics on the coverage of
        Tag per packages and the leaderboard of the game.
        """
        LOG.info('stats_action')

        if 'window' in kw:
            win = kw['window']
        else:
            win = Gtk.Window(title='GNOME Tagger - Statistics')
        win.set_default_size(400, 200)
        win.connect('delete-event', Gtk.main_quit)

        cursor = Gdk.Cursor(Gdk.CursorType.WATCH)
        self.get_root_window().set_cursor(cursor)
        Gdk.flush()

        if not self.statistics:
            url = '%s/statistics/' % TAGGERAPI
            try:
                data = requests.get(url, verify=not self.debug)
                jsondata = json.loads(data.text)
                self.statistics = jsondata['summary']
            except RequestException, err:
                error_box(
                    self,
                    "An error occured while trying to connect to %s"
                    "\nError: %s" % (url, err))
                cursor = Gdk.Cursor.new(Gdk.CursorType.ARROW)
                self.get_root_window().set_cursor(cursor)
                return

        listmodel = Gtk.ListStore(str, str)
        listmodel.append(['Total number of packages',
                         str(self.statistics['total_packages'])])
        listmodel.append(['Total number of tags',
                         str(self.statistics['total_unique_tags'])])
        listmodel.append(['Packages with no tags',
                         str(self.statistics['no_tags'])])
        listmodel.append(['Packages with tags',
                         str(self.statistics['with_tags'])])
        listmodel.append(['Average tags per package',
                         '%.2f' % self.statistics['tags_per_package']])
        listmodel.append(['Average tags per package '
                          '(that have at least one tag)',
                         '%.2f' % self.statistics[
                         'tags_per_package_no_zeroes']])

        # a treeview to see the data stored in the model
        view = Gtk.TreeView(model=listmodel)
        view.set_headers_visible(False)
        # for each column
        for i in range(2):
            # cellrenderer to render the text
            cell = Gtk.CellRendererText()
            # the text in the first column should be in boldface
            if i == 0:
                cell.props.weight_set = True
                cell.props.weight = Pango.Weight.BOLD
            # the column is created
            col = Gtk.TreeViewColumn('', cell, text=i)
            # and it is appended to the treeview
            view.append_column(col)

        if 'box' in kw:
            box = kw['box']
        else:
            box = Gtk.Table(6, 1, False)
        box.set_vexpand(True)
        box.set_hexpand(True)

        button = Gtk.Button(label="Ok")
        button.connect("clicked", self.win_close, win)
        button_refresh = Gtk.Button(label="Refresh")
        button_refresh.connect("clicked", self.refresh_stats, win, box)

        box.attach(view, 0, 5, 0, 1)
        box.attach(button_refresh, 3, 4, 1, 2,
                   xoptions=Gtk.AttachOptions.FILL | Gtk.AttachOptions.SHRINK)
        box.attach(button, 4, 5, 1, 2,
                   xoptions=Gtk.AttachOptions.FILL | Gtk.AttachOptions.SHRINK)

        # attach the grid to the window
        if not 'box' in kw:
            win.add(box)
        cursor = Gdk.Cursor.new(Gdk.CursorType.ARROW)
        self.get_root_window().set_cursor(cursor)
        win.show_all()

    def scores_action(self, button):
        """ Shows the leaderboard window with the scores information.
        """
        LOG.info('scores_action')
        win = Gtk.Window(title='GNOME Tagger - Leaderboard')
        win.connect('delete-event', Gtk.main_quit)
        win.set_default_size(400, 200)

        cursor = Gdk.Cursor(Gdk.CursorType.WATCH)
        self.get_root_window().set_cursor(cursor)
        Gdk.flush()

        try:
            url = '%s/leaderboard/' % TAGGERAPI
            data = requests.get(url, verify=not self.debug)
            jsondata = json.loads(data.text)
        except RequestException, err:
            error_box(
                self,
                "An error occured while trying to connect to %s"
                "\nError: %s" % (url, err))
            cursor = Gdk.Cursor.new(Gdk.CursorType.ARROW)
            self.get_root_window().set_cursor(cursor)
            return

        listmodel = Gtk.ListStore(str, str, str)
        for key in sorted([int(it) for it in jsondata.keys()]):
            listmodel.append([str(key),
                              jsondata[str(key)]['name'],
                              str(jsondata[str(key)]['score'])])

        headers = ['Rank', 'User', 'Score']
        # a treeview to see the data stored in the model
        view = Gtk.TreeView(model=listmodel)
        view.set_headers_visible(True)
        # for each column
        for i in range(3):
            # cellrenderer to render the text
            cell = Gtk.CellRendererText()
            # the text in the first column should be in boldface
            if i == 0:
                cell.props.weight_set = True
                cell.props.weight = Pango.Weight.BOLD
            # the column is created
            col = Gtk.TreeViewColumn(headers[i], cell, text=i)
            if i == 1:
                col.set_min_width(250)
            # and it is appended to the treeview
            view.append_column(col)

        # a grid to attach the widgets
        box = Gtk.Table(6, 1, False)
        box.set_vexpand(True)
        box.set_hexpand(True)

        button = Gtk.Button(label="Ok")
        button.connect("clicked", self.win_close, win)

        box.attach(view, 0, 5, 0, 1)
        box.attach(button, 4, 5, 1, 2, xoptions=Gtk.AttachOptions.FILL)

        # attach the grid to the window
        win.add(box)
        cursor = Gdk.Cursor.new(Gdk.CursorType.ARROW)
        self.get_root_window().set_cursor(cursor)
        win.show_all()

    def get_package(self, name=None):
        """ Retrieve the information about a package if the name if set, a
        random package if the name is None.
        """
        LOG.info('get_package')
        cursor = Gdk.Cursor(Gdk.CursorType.WATCH)
        self.get_root_window().set_cursor(cursor)
        Gdk.flush()
        msg = self.builder.get_object('label_msg')
        msg.set_text('')
        url = '%s/random/' % (TAGGERAPI)
        if name:
            url = '%s/%s/' % (TAGGERAPI, name)
        try:
            data = requests.get(url, verify=not self.debug)
            jsondata = json.loads(data.text)
            if data.status_code == 200:
                self.set_package_info(
                    name=jsondata['name'],
                    summary=jsondata['summary'],
                    tags=[tag['tag'] for tag in jsondata['tags']],
                    #icon_url=jsondata['icon'],
                    icon_url='https://apps.fedoraproject.org/packages/'
                         'images/icons/%s.png' % jsondata['name']
                )
            else:
                self.set_messsage(jsondata['error'], msgtype='error')
        except RequestException, err:
            error_box(
                self,
                "An error occured while trying to connect to %s"
                "\nError: %s" % (url, err))
        cursor = Gdk.Cursor.new(Gdk.CursorType.ARROW)
        self.get_root_window().set_cursor(cursor)

    def set_package_info(self, name, summary, tags, icon_url):
        """ Set the package information into the GUI.
        """
        self.pkgname = name

        image = self.builder.get_object('image_pkg')
        try:
            response = urllib2.urlopen(icon_url)
        except:
            response = urllib2.urlopen('https://apps.fedoraproject.org/'
                                       'packages/images/icons/'
                                       'package_128x128.png')
        loader = GdkPixbuf.PixbufLoader()
        loader.write(response.read())
        image.set_from_pixbuf(loader.get_pixbuf())
        loader.close()

        label = self.builder.get_object('label_pkg')
        label.set_text('<b>%s</b>\n%s' % (name, summary or ''))
        label.set_use_markup(True)

        treeview = self.builder.get_object('treeview1')
        liststore = Gtk.ListStore(str)
        for tag in tags:
            liststore.append([tag])
        treeview.set_model(liststore)

    def about_action(self, action, parameter):
        """ Show the about window. """
        LOG.info('about_action')
        aboutdialog = Gtk.AboutDialog()

        # lists of authors and documenters (will be used later)
        authors = ['Pierre-Yves Chibon', 'Ralph Bean']
        #documenters = ['GNOME Documentation Team']

        # we fill in the aboutdialog
        aboutdialog.set_program_name('GNOME Tagger')
        aboutdialog.set_copyright('Copyright \xc2\xa9 2013 Pierre-Yves Chibon')
        aboutdialog.set_authors(authors)
        #aboutdialog.set_documenters(documenters)
        aboutdialog.set_comments('Tag the Fedora packages and win badges!')
        aboutdialog.set_license('GPLv2 or any later version at your choice')
        aboutdialog.set_website('http://github.com/fedora-infra/gnome-tagger')
        aboutdialog.set_website_label('GNOME Tagger Website')

        aboutdialog.set_title('')

        aboutdialog.connect('response', self.on_close)
        # show the aboutdialog
        aboutdialog.show()

    def on_close(self, action, parameter=None):
        """ Called to close the about dialog. """
        action.destroy()

    def win_close(self, action, window):
        """ Called to close the statistics window. """
        window.destroy()

    def refresh_stats(self, action, window, box):
        """ Refresh the statistics on the statistics window. """
        LOG.info('refresh_stats')
        cursor = Gdk.Cursor(Gdk.CursorType.WATCH)
        self.get_root_window().set_cursor(cursor)
        Gdk.flush()

        data = requests.get('%s/statistics/' % TAGGERAPI,
                            verify=not self.debug)
        jsondata = json.loads(data.text)
        self.statistics = jsondata['summary']

        self.stats_action(window=window, box=box)

    def search_action(self, *args, **kw):
        """ Search the package using the search box entry. """
        LOG.info('search_action')
        entry_search = self.builder.get_object('entry_search')
        pkg_search = entry_search.get_text().strip()
        if pkg_search:
            self.get_package(name=pkg_search)
        entry_search.set_text('')

    def search_icon_action(self, entry, icon_pos, even):
        """ Search or clear the search box according to the icon clicked.
        """
        LOG.info('search_icon_action')
        if icon_pos == Gtk.EntryIconPosition.PRIMARY:
            self.search_action()
        else:
            entry_search = self.builder.get_object('entry_search')
            entry_search.set_text('')

    def page_loaded_action(self, view, param, window, callback):
        """ Callback function called when the a page is loaded.
        """
        if not view.get_title():
            page = view.get_main_frame().get_data_source().get_data().str
            if '"token":' in page:
                output = json.loads(page)
                window.destroy()
                LOG.info('output: {0}'.format(output))
                self.user = output
                callback()
        LOG.info('title: {0}'.format(view.get_title()))

    def get_user_info(self, callback):
        """ Pops-up a webkit window used against the Tagger API website
        to retrieve an API token used later on to authenticate the user.
        """
        window = Gtk.Window(title='GNOME Tagger - Login')
        window.connect('delete-event', Gtk.main_quit)

        view = WebKit.WebView()
        sw = Gtk.ScrolledWindow()
        window.add(sw)
        sw.add(view)
        window.set_size_request(600, 600)
        view.connect("load-finished", self.page_loaded_action,
                     window, callback)
        view.load_uri('%s/token/' % TAGGERAPI)

        window.show_all()


class GnomeTagger(Gtk.Application):

    def __init__(self, debug=False):
        Gtk.Application.__init__(self)
        self.debug = debug

    def do_activate(self):
        win = GnomeTaggerWindow(self)
        win.show_all()

    def do_startup(self):
        Gtk.Application.do_startup(self)

        # create a menu
        menu = Gio.Menu()
        # append to the menu three options
        menu.append('Statistics', 'app.statistics')
        menu.append('About', 'app.about')
        menu.append('Quit', 'app.quit')
        # set the menu as menu of the application
        self.set_app_menu(menu)

        # option 'quit'
        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', self.quit_action)
        self.add_action(quit_action)

    # callback function for 'quit'
    def quit_action(self, action, parameter):
        LOG.info('You have quit.')
        self.quit()


def setup_parser():
    parser = argparse.ArgumentParser()
    # General connection options
    parser.add_argument(
        '--debug', default=False, action='store_true',
        help='Provide additionnal output for debugging and use the '
            'stagging instance of fedora-tagger')
    return parser


def main():
    """ Main function. """
    parser = setup_parser()
    arg = parser.parse_args()
    LOG.setLevel(logging.DEBUG)
    if arg.debug:
        LOG.setLevel(logging.INFO)
        global TAGGERAPI
        TAGGERAPI = 'https://apps.stg.fedoraproject.org/tagger/api/v1/'
    app = GnomeTagger(arg.debug)
    exit_status = app.run([])
    sys.exit(exit_status)


if __name__ == '__main__':
    main()
