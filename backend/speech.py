import os
import tempfile

from pydub import AudioSegment
import speech_recognition as sr


def speech_to_text(audio_path):

    recognizer = sr.Recognizer()

    extension = os.path.splitext(audio_path)[1].lower()

    wav_path = audio_path

    if extension != ".wav":

        audio = AudioSegment.from_file(audio_path)

        fd, wav_path = tempfile.mkstemp(suffix=".wav")

        os.close(fd)

        audio.export(
            wav_path,
            format="wav"
        )

    with sr.AudioFile(wav_path) as source:

        recognizer.adjust_for_ambient_noise(
            source,
            duration=0.5
        )

        audio_data = recognizer.record(source)

    text = recognizer.recognize_google(
        audio_data,
        language="te-IN"
    )

    if wav_path != audio_path:

        try:
            os.remove(wav_path)
        except PermissionError:
            pass

    return text