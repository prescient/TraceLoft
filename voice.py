"""Voice club selection on this PC's microphone, offline (D76).

The golfer says a club ("seven iron", "pitching wedge", "putter") and it becomes the club for the next
shot, as if its button were tapped. Recognition runs locally with Vosk, restricted to the bag's club
names, so nothing leaves the PC, ordinary talk cannot pick a club, and no audio is stored.

Optional: Vosk and sounddevice are not in requirements-lock.txt, and the speech model lives outside
the repository (MODEL_DIR). Without them `available()` says what is missing and nothing else changes.
"""

import json
import os
import queue
import re
import threading
from pathlib import Path

MODEL_NAME = 'vosk-model-small-en-us-0.15'
MODEL_DIR = Path(os.environ.get('USERPROFILE', Path.home())) / 'GolfData' / 'voice' / MODEL_NAME
SAMPLE_RATE = 16000
MIN_CONFIDENCE = 0.75  # every word of the phrase must be at least this sure

NUMBERS = {
    '1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five', '6': 'six', '7': 'seven',
    '8': 'eight', '9': 'nine', '10': 'ten', '11': 'eleven',
}
WEDGES = {'PW': 'pitching wedge', 'GW': 'gap wedge', 'AW': 'approach wedge', 'SW': 'sand wedge',
          'LW': 'lob wedge', 'UW': 'utility wedge'}
KINDS = {'i': 'iron', 'iron': 'iron', 'w': 'wood', 'wood': 'wood', 'h': 'hybrid', 'hy': 'hybrid',
         'hybrid': 'hybrid', 'u': 'utility', 'ut': 'utility'}
TENS = {'4': 'forty', '5': 'fifty', '6': 'sixty'}
ONES = {'0': '', '1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five', '6': 'six',
        '7': 'seven', '8': 'eight', '9': 'nine'}


def degrees(number):
    """'56' -> 'fifty six' (wedge lofts 40-69)."""
    if len(number) == 2 and number[0] in TENS:
        return (TENS[number[0]] + ' ' + ONES[number[1]]).strip()
    return None


def spoken_names(label):
    """The phrases a golfer might say for a club label (lower case, words only)."""
    text = label.strip()
    upper = text.upper()
    names = []
    if upper in ('D', 'DR', 'DRIVER') or 'DRIVER' in upper:
        names.append('driver')
    if upper in ('PT', 'PUTTER') or 'PUTT' in upper:
        names.append('putter')
    if upper in WEDGES:
        names += [WEDGES[upper], ' '.join(upper.lower())]  # "pitching wedge", "p w"
    match = re.fullmatch(r'(\d{1,2})\s*-?\s*([a-zA-Z]+)', text)
    if match and match.group(2).lower() in KINDS:
        number = NUMBERS.get(match.group(1))
        if number:
            names.append(f'{number} {KINDS[match.group(2).lower()]}')
    loft = re.search(r'(\d{2})\s*(?:°|deg|degree)', text, re.I)
    if loft and degrees(loft.group(1)):
        names += [degrees(loft.group(1)) + ' degree', degrees(loft.group(1))]
    plain = re.sub(r'[^a-z ]', ' ', text.lower())
    plain = ' '.join(plain.split())
    if plain and not names and not any(ch.isdigit() for ch in text):
        names.append(plain)  # e.g. a custom "chipper"
    return list(dict.fromkeys(names))


def vocabulary(bag):
    """{phrase: club} for one bag; a phrase two clubs share is left out rather than guessed."""
    seen = {}
    for club in bag.get('clubs', []):
        for phrase in spoken_names(club['label']):
            seen.setdefault(phrase, []).append(club)
    return {phrase: clubs[0] for phrase, clubs in seen.items() if len(clubs) == 1}


def match(result, words):
    """The club for a Vosk final result, or None: the text must be a whole known phrase and every
    word confident enough."""
    text = (result.get('text') or '').strip()
    if text not in words:
        return None
    confidences = [w.get('conf', 0) for w in result.get('result', [])]
    if confidences and min(confidences) < MIN_CONFIDENCE:
        return None
    return words[text]


def available():
    """(True, '') or (False, what is missing) for the Relay page."""
    missing = []
    try:
        import vosk  # noqa: F401
    except ImportError:
        missing.append('the vosk package')
    try:
        import sounddevice  # noqa: F401
    except (ImportError, OSError):
        missing.append('the sounddevice package')
    if not MODEL_DIR.is_dir():
        missing.append(f'the speech model ({MODEL_NAME}) in {MODEL_DIR.parent}')
    return (not missing), ('Needs ' + ', '.join(missing) + '.' if missing else '')


class VoiceListener:
    """Listens on the default microphone in a background thread. `words()` returns the current
    {phrase: club}; `heard(club, phrase)` is called on the event loop for each recognized club."""

    def __init__(self, words, heard, loop, state):
        self.words, self.heard, self.loop, self.state = words, heard, loop, state
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, name='voice-clubs', daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(3)
        self.thread = None

    def _run(self):
        import sounddevice
        import vosk

        vosk.SetLogLevel(-1)
        audio = queue.Queue(maxsize=50)
        try:
            model = vosk.Model(str(MODEL_DIR))
            vocab = self.words()
            recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE, json.dumps([*vocab, '[unk]']))
            recognizer.SetWords(True)

            def captured(data, frames, time_info, status):
                if not audio.full():
                    audio.put(bytes(data))

            with sounddevice.RawInputStream(samplerate=SAMPLE_RATE, blocksize=4000, dtype='int16',
                                            channels=1, callback=captured):
                self.state.update(listening=True, error='')
                while not self.stop_event.is_set():
                    if self.words() != vocab:  # the bag changed: rebuild the grammar
                        vocab = self.words()
                        recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE, json.dumps([*vocab, '[unk]']))
                        recognizer.SetWords(True)
                    try:
                        data = audio.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        club = match(result, vocab)
                        if club:
                            self.loop.call_soon_threadsafe(self.heard, club, result['text'])
        except Exception as exc:  # microphone missing or busy, model unreadable
            self.state.update(error=f'Voice stopped: {exc}')
        finally:
            self.state['listening'] = False
