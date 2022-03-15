import pyaudio
import websockets
import asyncio
import base64
import json
import os
import pyglet
from ctypes import *
from contextlib import contextmanager
from gtts import gTTS

headers = {
    "authorization": "8fb4e965ed4a4303b8d250009e6ea54d",
    "content-type": "application/json"
}

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
 
    FRAMES_PER_BUFFER = 8192
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    p = pyaudio.PyAudio()
 
# starts recording
stream = p.open(
   format=FORMAT,
   channels=CHANNELS,
   rate=RATE,
   input=True,
   frames_per_buffer=FRAMES_PER_BUFFER
)


# the AssemblyAI endpoint we're going to hit
URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"




async def hello():
    temp_text = "Hello User"

    output = gTTS(text=temp_text, lang='en', slow=False)

    output.save("temp.mp3")

    sound = pyglet.media.load("/home/rjmchugh/senior_design/temp.mp3")

    sound.play()

    print("Output: " + temp_text)

    await asyncio.sleep(0.03)


async def handle_text(txt):
    if all(x in txt for x in ["Hey", "Alexa", "."]) in txt:
        await asyncio.gather(hello())

async def send_receive():
    auth_key = "8fb4e965ed4a4303b8d250009e6ea54d"
    print(f'Connecting websocket to url ${URL}')
    async with websockets.connect(
        URL,
        extra_headers=(("Authorization", auth_key),),
        ping_interval=5,
        ping_timeout=20
    ) as _ws:
        await asyncio.sleep(0.1)
        print("Receiving SessionBegins ...")
        session_begins = await _ws.recv()
        print(session_begins)
        print("Sending messages ...")

        # sending audio to speech recognition endpoint 
        async def send():
            while True:
                try:
                    data = stream.read(FRAMES_PER_BUFFER)
                    data = base64.b64encode(data).decode("utf-8")
                    json_data = json.dumps({"audio_data":str(data)})
                    await _ws.send(json_data)
                except websockets.exceptions.ConnectionClosedError as e:
                    print(e)
                    assert e.code == 4008
                    break
                except Exception as e:
                    assert False, "Not a websocket 4008 error"
                await asyncio.sleep(0.01)
            
            return True
        
        # reciving back text from the speech recognition endpoint
        async def receive():
            while True:
                try:
                    result_str = await _ws.recv()
                    temp = json.loads(result_str)['text']
                    print(temp)
                    await asyncio.gather(handle_text(temp))
                except websockets.exceptions.ConnectionClosedError as e:
                    print(e)
                    assert e.code == 4008
                    break
                except Exception as e:
                    assert False, "Not a websocket 4008 error"
        
        send_result, receive_result = await asyncio.gather(send(), receive())

asyncio.run(send_receive())