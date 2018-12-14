import pprint
import yaml
from pymediainfo import MediaInfo

VIDEO_FIELDS = [
    'format',
    'format_profile',
    'bit_rate',
    'width',
    'height',
    'frame_rate',
    'chroma_subsampling',
    'bit_depth',
    'default', 
    'forced']
AUDIO_FIELDS = [
    'format',
    'format_info',
    'duration',
    'bit_rate_mode',
    'bit_rate',
    'channel_s',
    'sampling_rate',
    'stream_size',
    'language',
    'service_kind',
    'default',
    'forced']
TEXT_FIELDS = [
    'format',
    'codec_id',
    'bit_rate',
    'title',
    'language',
    'default',
    'forced']
FIELDS = {
    'General': ['format', 'file_size', 'overall_bit_rate'],
    'Video': VIDEO_FIELDS,
    'Audio': AUDIO_FIELDS,
    'Text': TEXT_FIELDS
}

def languages(track):
    lang = []
    if track.language:
        lang.append(track.language)
    if track.other_language:
        lang.extend(track.other_language)
    return lang

def bitrate(track):
    if not track.bit_rate:
        return 0.0

    if isinstance(track.bit_rate, int) or isinstance(track.bit_rate, float):
        return float(track.bit_rate)
    elif isinstance(track.bit_rate, str):
        if '/' in track.bit_rate:
            num = track.bit_rate.split('/')
            return float(num[0])
        else:
            return float(track.bit_rate)

class VideoInfo:
    """
    Abstraction over MediaInfo, to assist in selecting tracks.
    """

    def __init__(self, source, lang='eng'):
        self.source = source
        self.lang = lang
        self.info = MediaInfo.parse(self.source)

        # Split the tracks info the expected types
        self.generalList = [t for t in self.info.tracks if t.track_type == 'General']
        self.videoList = [t for t in self.info.tracks if t.track_type == 'Video']
        self.audioList = [t for t in self.info.tracks if t.track_type == 'Audio']
        self.textList = [t for t in self.info.tracks if t.track_type == 'Text']

        assert len(self.videoList) == 1, "Multiple or no video tracks in input"
        assert len(self.generalList) == 1, "Multiple or no general tracks in input"

        # Sort by respective keys
        sorted(self.videoList, key=lambda t: t.width * t.height, reverse=True)
        sorted(self.audioList, key=lambda t: bitrate(t), reverse=True)
        sorted(self.textList, key=lambda t: bitrate(t), reverse=True)

        # Find matching language for audio
        lang_match = []
        lang_other = []
        for a in self.audioList:
            if lang in languages(a):
                lang_match.append(a)
            else:
                lang_other.append(a)
        lang_match.extend(lang_other)
        self.audioList = lang_match

        # Find matching language for subtitles
        lang_match = []
        lang_other = []
        for t in self.textList:
            if lang in languages(t):
                lang_match.append(t)
            else:
                lang_other.append(t)
        lang_match.extend(lang_other)
        self.textList = lang_match

        self.audioTracks = len(self.audioList)
        self.textTracks = len(self.textList)


    def general(self):
        """
        Returns container information.
        """
        return self.generalList[0]

    def video(self):
        """
        Return information about the video track.
        """
        return self.videoList[0]

    def audio(self, track=0):
        """
        Return information about the selected audio track.
        Sorted to place the best first.
        """
        return self.audioList[track]

    def text(self, track=0):
        """
        Return information about the selected text track.
        Sorted to place the best first.
        """
        return self.textList[track]

    def get_video_bitrate(self):
        return bitrate(self.video())

    def get_audio_bitrate(self, track=0):
        return bitrate(self.audio(track))

    def get_audio_lang(self, track=0):
        """
        Return the language for an audio track.
        """
        if self.audio(track).language:
            return self.audio(track).language
        return self.lang

    def resolution(self):
        return self.video().width * self.video().height

    def level(self):
        return float(self.video().format_profile.split('@L')[1])

    def report(self):
        msg = ""
        for t in self.info.tracks:
            source = t.to_data()
            d = {k: source[k] for k in FIELDS[t.track_type] if k in source}
            track_id = '0' if not t.track_id else t.track_id
            msg += "Track %s : %s\n" % (track_id, t.track_type)
            msg += yaml.dump(d, default_flow_style=False) + '\n'
        return msg
