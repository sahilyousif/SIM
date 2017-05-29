# measure_wav_mac.py
# Paul Boersma 2017-01-15
#
# A sample script that uses the Vokaturi library to extract the emotions from
# a wav file on disk. The file has to contain a mono recording.
#
# Call syntax:
#   python3 measure_wav_mac.py path_to_sound_file.wav

import sys
import scipy.io.wavfile

from kombu import Connection, Exchange, Queue
import datetime

sys.path.append("../SIM/libs/OpenVokaturi-2-1/api")
import Vokaturi

media_exchange = Exchange('media', 'direct', durable=True)
voice_queue = Queue('voice', exchange=media_exchange, routing_key='voice')


def voice_analysis():

    print ("Loading library...")
    Vokaturi.load("../SIM/libs/OpenVokaturi-2-1/lib/Vokaturi_mac.so")
    print ("Analyzed by: %s" % Vokaturi.versionAndLicense())

    print ("Reading sound file...")
    file_name = "demo.wav"
    (sample_rate, samples) = scipy.io.wavfile.read(file_name)
    print ("   sample rate %.3f Hz" % sample_rate)

    print ("Allocating Vokaturi sample array...")
    buffer_length = len(samples)
    print ("   %d samples, %d channels" % (buffer_length, samples.ndim))
    c_buffer = Vokaturi.SampleArrayC(buffer_length)
    if samples.ndim == 1:  # mono
    	c_buffer[:] = samples[:] / 32768.0
    else:  # stereo
    	c_buffer[:] = 0.5*(samples[:,0]+0.0+samples[:,1]) / 32768.0

    print ("Creating VokaturiVoice...")
    voice = Vokaturi.Voice (sample_rate, buffer_length)

    print ("Filling VokaturiVoice with samples...")
    voice.fill(buffer_length, c_buffer)

    print ("Extracting emotions from VokaturiVoice...")
    quality = Vokaturi.Quality()
    emotionProbabilities = Vokaturi.EmotionProbabilities()
    voice.extract(quality, emotionProbabilities)

    if quality.valid:
        with Connection('amqp://guest:guest@localhost:5672//') as conn:
            producer = conn.Producer(serializer='json')
            producer.publish({'Neutral': format(emotionProbabilities.neutrality,'.3f'),
                'Happy': format(emotionProbabilities.happiness,'.3f'),
                'Sad': format(emotionProbabilities.sadness,'.3f'),
                'Angry': format(emotionProbabilities.anger,'.3f'),
                'Fear': format(emotionProbabilities.fear,'.3f')},
                exchange=media_exchange, routing_key='voice',
                declare=[voice_queue])
        # print ("Neutral: %.3f" % emotionProbabilities.neutrality)
        # print ("Happy: %.3f" % emotionProbabilities.happiness)
        # print ("Sad: %.3f" % emotionProbabilities.sadness)
        # print ("Angry: %.3f" % emotionProbabilities.anger)
        # print ("Fear: %.3f" % emotionProbabilities.fear)
    else:
        print ("Not enough sonorancy to determine emotions")


    voice.destroy()