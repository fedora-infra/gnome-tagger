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

import urllib2
import json
import requests

from gi.repository import Gtk, GdkPixbuf

TAGGERAPI = 'http://209.132.184.171/'


class GnomeTagger(object):

    def __init__(self):
        self.pkgname = None

        self.builder = Gtk.Builder()
        self.builder.add_from_file("tagger.ui")
        window = self.builder.get_object("window1")
        window.set_title("Tagger")
        window.connect("delete-event", Gtk.main_quit)
        window.show_all()

        settings = Gtk.Settings.get_default()
        settings.props.gtk_button_images = True

        like_icon = GdkPixbuf.Pixbuf.new_from_file_at_size("like.png", 25, 25)
        dislike_icon = GdkPixbuf.Pixbuf.new_from_file_at_size("dislike.png",
                                                              25, 25)

        image = Gtk.Image()
        image.set_from_pixbuf(like_icon)
        image.show()
        likebutton = self.builder.get_object("button_like")
        likebutton.add(image)

        image = Gtk.Image()
        image.set_from_pixbuf(dislike_icon)
        image.show()
        dislikebutton = self.builder.get_object("button_dislike")
        dislikebutton.add(image)

        treeview = self.builder.get_object("treeview1")
        treeselection = treeview.get_selection()
        treeselection.set_mode(Gtk.SelectionMode.MULTIPLE)

        cell_tag = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn("Tags")
        column_text.pack_start(cell_tag, True)
        column_text.set_attributes(cell_tag, text=0)
        treeview.append_column(column_text)

        dic = {
            "on_button_next_pkg_clicked": self.next_pkg_action,
            "on_button_add_tag_clicked": self.add_tag_action,
            "on_button_like_clicked": self.like_action,
            "on_button_dislike_clicked": self.dislike_action,
            "on_button_stats_clicked": self.stats_action,
        }
        self.builder.connect_signals(dic)

        self.get_package('firefox')

    def next_pkg_action(self, *args, **kw):
        """ Retrieve information about the next (random) package and update
        the GUI accordingly.
        """
        print "next_pkg_action"
        msg = self.builder.get_object("label_msg")
        msg.set_text('')
        self.get_package()

    def add_tag_action(self, *args, **kw):
        """ Retrieve the tags from `entry_tag` and send them to the server,
        update the GUI afterward.
        """
        print "add_tag_action"
        msg = self.builder.get_object("label_msg")
        msg.set_text('')
        tagfield = self.builder.get_object("entry_tag")
        entries = tagfield.get_text()
        entries = [entry.strip() for entry in entries.split(',')]
        tagfield.set_text('')
        if entries != ['']:
            data = {'pkgname': self.pkgname, 'tag': ','.join(entries)}
            req = requests.put('%s/tag/guake/' % TAGGERAPI, data=data)
            print req.text
            jsonreq = json.loads(req.text)
            if req.status_code != 200:
                msg.set_text(jsonreq['error'])
            else:
                msg.set_text('\n'.join(jsonreq['messages']))
            self.get_package(self.pkgname)

    def like_action(self, *args, **kw):
        """ Retrieve the list of tags which are selected and send to the
        server that they have been 'licked'.
        If no tags are selected show an error dialog.
        """
        print "like_click"
        msg = self.builder.get_object("label_msg")
        msg.set_text('')
        data = {'pkgname': self.pkgname, 'vote':'1'}
        treeview = self.builder.get_object("treeview1")
        selection = treeview.get_selection()
        tree_model, rows = selection.get_selected_rows()
        for tree_iter in rows:
            if tree_iter:
                tag = tree_model[tree_iter][0]
                data['tag'] = tag
                req = requests.put('%s/vote/guake/' % TAGGERAPI,
                                   data=data)
                print req.text
                jsonreq = json.loads(req.text)
                if req.status_code != 200:
                    msg.set_text(jsonreq['error'])
                else:
                    msg.set_text('\n'.join(jsonreq['messages']))

    def dislike_action(self, *args, **kw):
        """ Retrieve the list of tags which are selected and send to the
        server that they have been 'dislicked'.
        If no tags are selected show an error dialog.
        """
        print "dislike_click"
        msg = self.builder.get_object("label_msg")
        msg.set_text('')
        data = {'pkgname': self.pkgname, 'vote':'-1'}
        treeview = self.builder.get_object("treeview1")
        selection = treeview.get_selection()
        tree_model, rows = selection.get_selected_rows()
        for tree_iter in rows:
            if tree_iter:
                tag = tree_model[tree_iter][0]
                data['tag'] = tag
                req = requests.put('%s/vote/guake/' % TAGGERAPI,
                                   data=data)
                print req.text
                jsonreq = json.loads(req.text)
                if req.status_code != 200:
                    msg.set_text(jsonreq['error'])
                else:
                    msg.set_text('\n'.join(jsonreq['messages']))

    def stats_action(self, *args, **kw):
        """ Retrieves statistics from the server and display them in a new
        dialog.
        These statistics include general statistics on the coverage of Tag
        per packages and the leaderboard of the game.
        """
        print "stats_action"

    def get_package(self, name=None):
        """ Retrieve the information about a package if the name if set, a
        random package if the name is None.
        """
        if name:
            data = requests.get(TAGGERAPI + name + '/')
        else:
            data = requests.get(TAGGERAPI + '/random/')
        jsondata = json.loads(data.text)
        self.set_package_info(
            name=jsondata['name'],
            summary=jsondata['summary'],
            tags=[tag['tag'] for tag in jsondata['tags']],
            icon_url=jsondata['icon'],
        )

    def set_package_info(self, name, summary, tags, icon_url):
        """ Set the package information into the GUI.
        """
        self.pkgname = name

        image = self.builder.get_object("image_pkg")
        response = urllib2.urlopen(icon_url)
        loader = GdkPixbuf.PixbufLoader()
        loader.write(response.read())
        image.set_from_pixbuf(loader.get_pixbuf())
        loader.close()

        label = self.builder.get_object("label_pkg")
        label.set_text("<b>%s</b>\n%s" % (name, summary or ''))
        label.set_use_markup(True)

        treeview = self.builder.get_object("treeview1")
        liststore = Gtk.ListStore(str)
        for tag in tags:
            liststore.append([tag])
        treeview.set_model(liststore)


def main():
    """ Main function. """
    GnomeTagger()
    Gtk.main()


if __name__ == '__main__':
    main()
