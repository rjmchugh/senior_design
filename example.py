import sys
# from configure import auth_key
import requests
import pprint
import pyaudio
import wave
from time import sleep
from ctypes import *
from contextlib import contextmanager

headers = {
    "authorization": "8fb4e965ed4a4303b8d250009e6ea54d",
    "content-type": "application/json"
}
transcript_endpoint = "https://api.assemblyai.com/v2/transcript"
upload_endpoint = 'https://api.assemblyai.com/v2/upload'

ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)

def py_error_handler(filename, line, function, err, fmt):
    pass

c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)

@contextmanager
def noalsaerr():
    asound = cdll.LoadLibrary('libasound.so')
    asound.snd_lib_error_set_handler(c_error_handler)
    yield
    asound.snd_lib_error_set_handler(None)

with noalsaerr():

    chunk = 2048
    channels = 2
    fs = 44100
    seconds = int(input("How many seconds do you want to talk?"))
    filename = "temp.wav"
    p = pyaudio.PyAudio()

    print('Recording')

stream = p.open( format=pyaudio.paInt16,rate=fs, channels = channels,
                frames_per_buffer=chunk, input=True)
frames = []

for i in range(0, int(fs / chunk * seconds)):
    frames.append(stream.read(chunk))

stream.stop_stream()
stream.close()
p.terminate()

wf = wave.open(filename, 'wb')
wf.setnchannels(2)
wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
wf.setframerate(44100)
wf.writeframes(b''.join(frames))
wf.close()

def read_file():
    with open('temp.wav', 'rb') as _file:
        while True:
            data = _file.read(5242880)
            if not data:
                break
            yield data

upload_response = requests.post(
    upload_endpoint,
    headers=headers, data=read_file()
)

print('Audio file uploaded')
transcript_request = {'audio_url': upload_response.json()['upload_url']}
transcript_response = requests.post(transcript_endpoint, json=transcript_request, headers=headers)
print('Transcription Requested')
# pprint.pprint(transcript_response.json())
polling_response = requests.get(transcript_endpoint+"/"+transcript_response.json()['id'], headers=headers)
filename = transcript_response.json()['id'] + '.txt'
while polling_response.json()['status'] != 'completed':
    sleep(10)
    polling_response = requests.get(transcript_endpoint+"/"+transcript_response.json()['id'], headers=headers)
    # print("File is", polling_response.json()['status'])
# with open(filename, 'w') as f:
#     f.write(polling_response.json()['text'])
print(polling_response.json()['text'])
# print('Transcript saved to', filename)


