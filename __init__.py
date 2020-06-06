from os.path import dirname
import re

from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.util.log import LOG
from adapt.intent import IntentBuilder

from .helpers import kodi_tools

_author__ = 'PCWii'
# Release - '20200603 - Covid-19 Build'


class CPKodiSkill(CommonPlaySkill):
    def __init__(self):
        super(CPKodiSkill, self).__init__('CPKodiSkill')
        self.kodi_path = ""
        self.kodi_image_path = ""
        self._is_setup = False
        self.notifier_bool = False
        self.regexes = {}
        #self.settings_change_callback = self.on_websettings_changed

    def initialize(self):
        self.load_data_files(dirname(__file__))
        self.on_websettings_changed()
        self.add_event('recognizer_loop:wakeword', self.handle_listen)
        self.add_event('recognizer_loop:utterance', self.handle_utterance)
        self.add_event('speak', self.handle_speak)
        """
           All basic intents are added here
           These are non cps intents 
        """
        # eg. stop the movie
        stop_intent = IntentBuilder("StopIntent"). \
            require("StopKeyword").one_of("ItemKeyword", "KodiKeyword", "YoutubeKeyword").build()
        self.register_intent(stop_intent, self.handle_stop_intent)

        # eg. pause the movie
        pause_intent = IntentBuilder("PauseIntent"). \
            require("PauseKeyword").one_of("ItemKeyword", "KodiKeyword", "YoutubeKeyword").build()
        self.register_intent(pause_intent, self.handle_pause_intent)

        # eg. resume (unpause) the movie
        resume_intent = IntentBuilder("ResumeIntent"). \
            require("ResumeKeyword").one_of("ItemKeyword", "KodiKeyword", "YoutubeKeyword").build()
        self.register_intent(resume_intent, self.handle_resume_intent)

        # eg. turn kodi notifications on
        notification_on_intent = IntentBuilder("NotifyOnIntent"). \
            require("NotificationKeyword").require("OnKeyword"). \
            require("KodiKeyword").build()
        self.register_intent(notification_on_intent, self.handle_notification_on_intent)

        # eg. turn kodi notifications off
        notification_off_intent = IntentBuilder("NotifyOffIntent"). \
            require("NotificationKeyword").require("OffKeyword"). \
            require("KodiKeyword").build()
        self.register_intent(notification_off_intent, self.handle_notification_off_intent)

    def on_websettings_changed(self):  # called when updating mycroft home page
        # if not self._is_setup:
        LOG.info('Websettings have changed! Updating path data')
        kodi_ip = self.settings.get("kodi_ip", "192.168.0.32")
        kodi_port = self.settings.get("kodi_port", "8080")
        kodi_user = self.settings.get("kodi_user", "")
        kodi_pass = self.settings.get("kodi_pass", "")
        try:
            if kodi_ip and kodi_port:
                kodi_ip = self.settings["kodi_ip"  ]
                kodi_port = self.settings["kodi_port"]
                kodi_user = self.settings["kodi_user"]
                kodi_pass = self.settings["kodi_pass"]
                self.kodi_path = "http://" + kodi_user + ":" + kodi_pass + "@" + kodi_ip + ":" + str(kodi_port) + \
                                 "/jsonrpc"
                LOG.info(self.kodi_path)
                self.kodi_image_path = "http://" + kodi_ip + ":" + str(kodi_port) + "/image/"
                self._is_setup = True
        except Exception as e:
            LOG.error(e)

    # listening event used for kodi notifications
    def handle_listen(self, message):
        voice_payload = "Listening"
        if self.notifier_bool:
            try:
                self.post_kodi_notification(voice_payload)
            except Exception as e:
                LOG.info('An error was detected in: handle_listen')
                LOG.error(e)
                self.on_websettings_changed()

    # utterance event used for kodi notifications
    def handle_utterance(self, message):
        utterance = message.data.get('utterances')
        voice_payload = utterance
        if self.notifier_bool:
            try:
                self.post_kodi_notification(voice_payload)
            except Exception as e:
                LOG.info('An error was detected in: handle_utterance')
                LOG.error(e)
                self.on_websettings_changed()

    # mycroft speaking event used for kodi notificatons
    def handle_speak(self, message):
        voice_payload = message.data.get('utterance')
        if self.notifier_bool:
            try:
                self.post_kodi_notification(voice_payload)
            except Exception as e:
                LOG.info('An error was detected in: handle_speak')
                LOG.error(e)
                self.on_websettings_changed()

    # stop film was requested in the utterance
    def handle_stop_intent(self, message):
        try:
            self.stop_all()
        except Exception as e:
            LOG.info('An error was detected in: handle_stop_intent')
            LOG.error(e)
            self.on_websettings_changed()

    # pause film was requested in the utterance
    def handle_pause_intent(self, message):
        try:
            self.pause_all()
        except Exception as e:
            LOG.info('An error was detected in: handle_pause_intent')
            LOG.error(e)
            self.on_websettings_changed()

    # resume the film was requested in the utterance
    def handle_resume_intent(self, message):
        try:
            self.resume_all()
        except Exception as e:
            LOG.info('An error was detected in: handle_resume_intent')
            LOG.error(e)
            self.on_websettings_changed()

    # turn notifications on requested in the utterance
    def handle_notification_on_intent(self, message):
        self.notifier_bool = True
        self.speak_dialog("notification", data={"result": "On"})

    # turn notifications off requested in the utterance
    def handle_notification_off_intent(self, message):
        self.notifier_bool = False
        self.speak_dialog("notification", data={"result": "Off"})

    def translate_regex(self, regex):
        # opens the file
        self.regexes = {}
        if regex not in self.regexes:
            path = self.find_resource(regex + '.regex')
            if path:
                with open(path) as f:
                    string = f.read().strip()
                self.regexes[regex] = string
            else:
                return None
        else:
            return None
        return self.regexes[regex]

    def get_request_details(self, phrase):
        """
            All requests types are added here and return the requested items
            A <item>.type.regex should exist in the local/en-us
        """
        album_type = re.match(self.translate_regex('album.type'), phrase)
        artist_type = re.match(self.translate_regex('artist.type'), phrase)
        movie_type = re.match(self.translate_regex('movie.type'), phrase)
        song_type = re.match(self.translate_regex('song.type'), phrase)
        if album_type:
            request_type = 'album'
            request_item = album_type.groupdict()['album']
        elif artist_type:
            request_type = 'artist'
            request_item = artist_type.groupdict()['artist']
        elif movie_type:
            request_type = 'movie'
            request_item = movie_type.groupdict()['movie']
        elif song_type:
            request_type = 'title'
            request_item = song_type.groupdict()['title']
        else:
            request_type = None
            request_item = None
        return request_item, request_type  # returns the request details and the request type


    def CPS_match_query_phrase(self, phrase):
        """
            The method is invoked by the PlayBackControlSkill.
        """
        LOG.info('CPKodiSkill received the following phrase: ' + phrase)
        try:
            request_item, request_type = self.get_request_details(phrase)  # extract the movie name from the phrase
            if (request_item is None) or (request_type is None):
                LOG.info('GetRequest returned None')
                return None
            else:
                LOG.info("Requested search: " + str(request_item) + ", of type: " + str(request_type))
            if "movie" in request_type:
                results = kodi_tools.get_requested_movies(self.kodi_path, request_item)
                LOG.info("Possible movies matches are: " + str(results))
            if ("album" in request_type) or ("title" in request_type) or ("artist" in request_type):
                results = kodi_tools.get_requested_music(self.kodi_path, request_item, request_type)
                LOG.info("Searching for music")
            if results is None:
                LOG.info("Found Nothing!")
                return None  # no match found by this skill
            else:
                if len(results) > 0:
                    match_level = CPSMatchLevel.EXACT
                    data = {
                        "library": results,
                        "request": request_item,
                        "type": request_type
                    }
                    LOG.info('Searching Kodi found a matching playable item!')
                    return phrase, match_level, data
                else:
                    return None  # until a match is found
        except Exception as e:
            LOG.info('An error was detected in: CPS_match_query_phrase')
            LOG.error(e)
            self.on_websettings_changed()

    def CPS_start(self, phrase, data):
        """ Starts playback.
            Called by the playback control skill to start playback if the
            skill is selected (has the best match level)
        """
        LOG.info('cpKodi Library: ' + str(data["library"]))
        LOG.info('cpKodi Request: ' + str(data["request"]))
        LOG.info('cpKodi Type: ' + str(data["type"]))
        self.queue_and_play_music(data["library"])
        #pass

    def queue_and_play_music(self, music_playlist):
        LOG.info(str(music_playlist))
        result = kodi_tools.playlist_clear(self.kodi_path)
        #kodi_tools.clear_playlist(self.kodi_path)
        playlist_dict = []
        for each_song in music_playlist:
            song_id = str(each_song["songid"])
            playlist_dict.append(song_id)
        LOG.info("Adding to Kodi Playlist: " + str(playlist_dict))
        result = kodi_tools.add_song_playlist(self.kodi_path, playlist_dict)
        #self.play_normal()


def create_skill():
    return CPKodiSkill()
