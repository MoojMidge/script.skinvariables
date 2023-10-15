# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
from xbmcgui import ListItem
from xbmc import ENGLISH_NAME, convertLanguage, getLocalizedString
from jurialmunkey.jsnrpc import get_jsonrpc
from jurialmunkey.litems import Container


class ListGetPlayerStreams(Container):
    __cache__ = {}

    CH_FORMATS = {
        8: getLocalizedString(34110),
        7: getLocalizedString(34109),
        6: getLocalizedString(34108),
        5: getLocalizedString(34106),
        4: getLocalizedString(34104),
        3: getLocalizedString(34102),
        2: getLocalizedString(34101),
        1: getLocalizedString(34101),
    }

    EXT_LABEL = getLocalizedString(21602)

    TYPE_PROPS = {
        'audio': ('audiostreams', 'currentaudiostream'),
        'subtitle': ('subtitles', 'currentsubtitle'),
        'video': ('videostreams', 'currentvideostream'),
    }

    def get_directory(self, stream_type='subtitle', **kwargs):

        def _get_items(stream_type=None):
            def make_item(stream, stream_group):
                idx = stream.get('index', 0)
                if stream_group == 'subtitle':
                    stream_type = 'subtitle'
                elif 'audio' in stream_group:
                    stream_type = 'audio'
                elif 'video' in stream_group:
                    stream_type = 'video'

                path = f'plugin://script.skinvariables/?info=set_player_streams&stream_index={idx}&stream_type={stream_type}'
                props = {k: v for k, v in stream.items() if v}
                props['StreamType'] = stream_type

                if stream_type == 'video':
                    label = stream.get('name', '')
                    label2 = None
                else:
                    label = stream.get('language', 'und')
                    label2 = stream.get('name', '')

                    # Use language name if stream name is not provided
                    if not label2 or ListGetPlayerStreams.EXT_LABEL in label2:
                        lang = convertLanguage(
                            label, ENGLISH_NAME
                        ).split(';')[0]
                        if label2:
                            props['IsExternal'] = 'true'
                            label2 = label2.replace(
                                ListGetPlayerStreams.EXT_LABEL, lang
                            )
                        else:
                            props['IsExternal'] = 'false'
                            label2 = lang

                    # This is a workaround for a bug with InputStream.Adaptive
                    # where the codec gets added to the stream name as
                    # "<name> - <codec> " and is not parsed as a stream property
                    elif stream_type == 'audio':
                        name_tokens = label2.split(' ')
                        if not name_tokens[-1] and name_tokens[-2]:
                            props['codec'] = name_tokens[-2]
                            label2 = ' '.join(name_tokens[:-3])

                if 'channels' in props:
                    props['ChannelFormat'] = (
                        ListGetPlayerStreams.CH_FORMATS.get(props['channels'], '')
                    )

                # Use stream['bitrate'] here so that there is a "0 kbps" value
                # in the OSD to indicate stream has not been scanned properly
                if 'bitrate' in stream:
                    props['BitrateKbps'] = stream['bitrate'] // 1000

                if stream_idx.get(f'current{stream_group}') == idx:
                    props['IsCurrent'] = 'true'
                props['IsFolder'] = 'false'

                listitem = ListItem(label=label, label2=label2, path=path, offscreen=True)
                listitem.setProperties(props)
                return listitem

            if stream_type:
                properties = ListGetPlayerStreams.TYPE_PROPS.get(stream_type)
            else:
                properties = [
                    stream_type
                    for types in ListGetPlayerStreams.TYPE_PROPS.values()
                    for stream_type in types
                ]

            all_streams = None
            response = get_jsonrpc('Player.GetProperties',
                                   {'playerid': 1, 'properties': properties})
            if response:
                all_streams = response.get('result')
            if not all_streams:
                return []

            stream_idx = {
                'currentaudiostream': 0,
                'currentsubtitle': 0,
                'currentvideostream': 0,
            }
            for stream_type in stream_idx:
                current_stream = all_streams.get(stream_type)
                if current_stream:
                    stream_idx[stream_type] = current_stream.get('index')
                    del all_streams[stream_type]

            return [
                make_item(stream, stream_group[:-1])
                for stream_group, streams in all_streams.items() if streams
                for stream in streams if stream
            ]

        cache_index = None
        items = None

        if 'reload' in kwargs:
            cache_index = kwargs['reload']
            if cache_index in ListGetPlayerStreams.__cache__:
                items = ListGetPlayerStreams.__cache__[cache_index]

        if not items:
            items = _get_items()

        if cache_index:
            ListGetPlayerStreams.__cache__[cache_index] = items

        cache_items = ListGetPlayerStreams.__cache__.keys()
        if len(cache_items) > 5:
            for old_entry in cache_items[:-5]:
                del ListGetPlayerStreams.__cache__[old_entry]

        self.add_items(
            {'url': li.getPath(),
             'listitem': li,
             'isFolder': li.getProperty('IsFolder').lower() == 'true'}
            for li in items
            if li and li.getProperty('StreamType') == stream_type
        )


class ListSetPlayerStreams(Container):
    def get_directory(self, stream_type='subtitle', stream_index=None, **kwargs):
        if not stream_type or stream_index is None:
            return
        if stream_type == 'audio':
            from resources.lib.method import set_player_audiostream
            set_player_audiostream(stream_index)
            return
        if stream_type == 'subtitle':
            from resources.lib.method import set_player_subtitle
            set_player_subtitle(stream_index)
            return
        if stream_type == 'video':
            from resources.lib.method import set_player_videostream
            set_player_videostream(stream_index)
            return
