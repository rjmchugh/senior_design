# adapted from code on www.assemblyai.com
# https://www.assemblyai.com/blog/real-time-speech-recognition-with-python/
# example for using installed deepspeech model
# https://www.assemblyai.com/blog/deepspeech-for-dummies-a-tutorial-and-overview-part-1/
import pyaudio
import websockets
import asyncio
import base64
import json
import pyttsx3
import firebase_admin
import datetime
from firebase_admin import credentials
from firebase_admin import firestore
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
from ctypes import *
from contextlib import contextmanager

cred = credentials.Certificate('benten-imani-doll-firebase-adminsdk-bqh56-515e72e62d.json')

firebase_admin.initialize_app(cred)

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


# the AssemblyAI endpoint we hit
URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

async def upload_to_database(doll, text):
	db = firestore.client()
	doc_ref = db.collection('Messages').document('BROhk27nFKRABbRQ0q9f')
	doc_ref.update({u'conversation': firestore.ArrayUnion([
	{u'isDoll' : doll, u'speech' : text}])})
	doc_ref.update({u'date': str(datetime.date.today())})
#, u'time' : str(datetime.date.today())

async def voice_out(text_input):
	await upload_to_database(True, text_input)
	tts = gTTS(text_input, lang='en')
	tts.save('temp.mp3')


	tts_out = AudioSegment.from_file('temp.mp3')
	play(tts_out)

	print("Output: " + text_input)
	await asyncio.sleep(0.03)

async def handle_text(txt):
	#rasa code
	# r = requests.post('http://localhost:5002/webhooks/rest/webhook', json={"sender": sender, "message": message})
	await upload_to_database(False, txt)
	if all(x in str(txt) for x in ["Hi", "computer", "."]):
		await asyncio.gather(voice_out("Hello!"))
	elif all(x in str(txt) for x in ["Good", "morning", "."]):
		await asyncio.gather(voice_out("Did you have a balanced breakfast today?"))
	elif all(x in str(txt) for x in ["breakfast", "example",  "."]):
		await asyncio.gather(voice_out("Some eggs fruit and orange juice."))
	elif all(x in str(txt) for x in ["exactly", "eat",  "."]):
		await asyncio.gather(voice_out("Perfect! Lets play!"))

async def send_receive():
	start = True;
	if (start):
		await voice_out("Hello!")
		start = False;
	
	auth_key = "8fb4e965ed4a4303b8d250009e6ea54d"
	async with websockets.connect(
		URL,
		extra_headers=(("Authorization", auth_key),),
		ping_interval=5,
		ping_timeout=20
	) as _ws:
		await asyncio.sleep(0.1)
		print("Receiving SessionBegins ...")
		session_begins = await _ws.recv()
		# print(session_begins)
		print("Sending messages ...")

		# sending audio to speech recognition endpoint 
		async def send():
			while True:
				try:
					data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
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
					if(temp != ""):
						print(temp)
					if "." in temp:
						await asyncio.gather(handle_text(temp))
				except websockets.exceptions.ConnectionClosedError as e:
					print(e)
					assert e.code == 4008
					break
				except Exception as e:
					assert False, "Not a websocket 4008 error"
        
		send_result, receive_result = await asyncio.gather(send(), receive())

asyncio.run(send_receive())
