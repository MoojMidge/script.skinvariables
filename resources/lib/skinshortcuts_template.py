# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
import xbmc
import xbmcgui
import xbmcaddon
from json import loads
from jurialmunkey.futils import load_filecontent, write_skinfile, make_hash
from xml.sax.saxutils import escape

ADDON = xbmcaddon.Addon()


class SkinShortcutsTemplate(object):
    def __init__(self, template: str = None):
        self.template = f'skinvariables-generator-{template}' if template else 'skinvariables-generator'
        self.hashname = f'script-{self.template}-hash'
        self.content = load_filecontent(f'special://skin/shortcuts/{self.template}.json')
        self.meta = loads(self.content) or {}
        self.filename = self.meta['output']
        self.filepath = f'special://skin/shortcuts/{self.filename}'

    @staticmethod
    def create_xml(meta, header=None, footer=None, pregen=None, getnfo=None):

        def _make_template(i, d):
            template = i.pop("template")
            template = load_filecontent(f'special://skin/shortcuts/{template}')
            template = template.format(**dict(d, **{k: _make_template(v, d) if isinstance(v, dict) else v for k, v in i.items()}, **(getnfo or {})))
            return template

        _pregen = {k: _make_template(v, {}) for k, v in pregen.items()} if pregen else {}
        _header = [header] if header else []
        _footer = [footer] if footer else []
        content = _header + [_make_template(i, _pregen) for i in meta] + _footer

        return '\n'.join(content)

    def update_xml(self, force=False, no_reload=False, genxml='', **kwargs):
        if not self.meta:
            return

        hashvalue = '_'.join([f'{k}.{v}' for k, v in kwargs.items()])
        hashvalue = f'{self.content}{load_filecontent(self.filepath)}{genxml}{hashvalue}'
        hashvalue = f'{make_hash(hashvalue)}--{xbmc.getInfoLabel("System.ProfileName")}'

        if not force:  # Allow overriding over built check
            last_version = xbmc.getInfoLabel(f'Skin.String({self.hashname})')
            if hashvalue and last_version and hashvalue == last_version:
                return  # Already updated

        p_dialog = xbmcgui.DialogProgressBG()
        p_dialog.create(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32000))

        self.meta['genxml'] += [{k: v for j in i.split('|') for k, v in (j.split('='), )} for i in genxml.split('||')] if genxml else []
        self.meta['getnfo'] = {k: xbmc.getInfoLabel(v) for k, v in self.meta['getnfo'].items()} if 'getnfo' in self.meta else {}
        self.meta['getnfo'].update(kwargs)
        self.meta['getnfo'].update({f'{k}_escaped': escape(v) for k, v in self.meta['getnfo'].items() if not k.endswith('_escaped')})

        content = self.create_xml(
            self.meta['genxml'],
            header=self.meta.get('header'),
            footer=self.meta.get('footer'),
            pregen=self.meta.get('global'),
            getnfo=self.meta['getnfo'])

        # Save to folder
        write_skinfile(folders=['shortcuts'], filename=self.filename, content=content, hashvalue=hashvalue, hashname=self.hashname)

        p_dialog.close()
        xbmc.executebuiltin('ReloadSkin()') if not no_reload else None
