import openai
import speech_recognition as sr
from gtts import gTTS
from elevenlabs import generate, save, set_api_key, voices
import sounddevice as sd
import soundfile as sf

import ollama

from dotenv import load_dotenv
from os import getenv, path
from json import load, dump, dumps, JSONDecodeError

class Waifu:
    def __init__(self) -> None:
        self.mic = None
        self.recogniser = None

        self.user_input_service = None
        self.stt_duration = None

        self.chatbot_service = None
        self.chatbot_model = None
        self.chatbot_temperature = None
        self.chatbot_personality_file = None

        self.message_history = []
        self.context = []

        self.tts_service = None
        self.tts_voice = None
        self.tts_model = None


    def initialize(self, user_input_service:str = None, stt_duration:float = None, mic_index:int = None,
                    chatbot_service:str = None, chatbot_model:str = None, chatbot_temperature:float = None, personality_file:str = None,
                    tts_service:str = None, output_device = None, tts_voice:str = None, tts_model:str = None) -> None:
        load_dotenv()

        self.update_user_input(user_input_service=user_input_service, stt_duration=stt_duration)
        self.mic = sr.Microphone(device_index=mic_index)
        self.recogniser = sr.Recognizer()
        
        if chatbot_service == 'openai' or user_input_service == 'whisper':
            openai.api_key = getenv("OPENAI_API_KEY")
        
        self.update_chatbot(service = chatbot_service, model = chatbot_model, temperature = chatbot_temperature, personality_file = personality_file)
        self.__load_chatbot_data()

        self.update_tts(service=tts_service, output_device=output_device, voice=tts_voice, model=tts_model)

    def update_user_input(self, user_input_service:str = 'whisper', stt_duration:float = 0.5) -> None:
        if user_input_service:
            self.user_input_service = user_input_service
        elif self.user_input_service is None:
            self.user_input_service = 'whisper'

        if stt_duration:
            self.stt_duration = stt_duration
        elif self.stt_duration is None:
            self.stt_duration = 0.5

    def update_chatbot(self, service:str = 'openai', model:str = 'gpt-3.5-turbo', temperature:float = 0.5, personality_file:str = 'personality.txt') -> None:
        if service:
            self.chatbot_service = service
        elif self.chatbot_service is None:
            self.chatbot_service = 'openai'

        if model:
            self.chatbot_model = model
        elif self.chatbot_model is None:
            self.chatbot_model = 'gpt-3.5-turbo'

        if temperature:
            self.chatbot_temperature = temperature
        elif self.chatbot_temperature is None:
            self.chatbot_temperature = 0.5

        if personality_file:
            self.chatbot_personality_file = personality_file
        elif self.chatbot_personality_file is None:
            self.chatbot_personality_file = 'personality.txt'

    def update_tts(self, service:str = 'google', output_device = None, voice:str = None, model:str = None) -> None:
        if service:
            self.tts_service = service
        elif self.tts_service is None:
            self.tts_service = 'google'

        if service == 'elevenlabs':
            set_api_key(getenv('ELEVENLABS_API_KEY'))

        if voice:
            self.tts_voice = voice
        elif self.tts_voice is None:
            self.tts_voice = 'Elli'

        if model:
            self.tts_model = model
        elif self.tts_model is None:
            self.tts_model = 'eleven_monolingual_v1'

        if output_device is not None:
            try:
                sd.check_output_settings(output_device)
                sd.default.samplerate = 44100
                sd.default.device = output_device
            except sd.PortAudioError:
                print("Invalid output device! Make sure you've launched VB-Cable.\n",
                       "Check that you've choosed the correct output_device in initialize method.\n", 
                       "From the list below, select device that starts with 'CABLE Input' and set output_device to it's id in list.\n",
                       "If you still have this error try every device that starts with 'CABLE Input'. If it doesn't help please create GitHub issue.")
                print(sd.query_devices())
                raise

    def get_audio_devices(self):
        return sd.query_devices()

    def get_user_input(self, service:str = None, stt_duration:float = None) -> str:
        service = self.user_input_service if service is None else service
        stt_duration = self.stt_duration if stt_duration is None else stt_duration

        supported_stt_services = ['whisper', 'google']
        supported_text_services = ['console']

        result = ""
        if service in supported_stt_services:
            result = self.__recognise_speech(service, duration=stt_duration)
        elif service in supported_text_services:
            result = self.__get_text_input(service)
        else:
            raise ValueError(f"{service} servise doesn't supported. Please, use one of the following services: {supported_stt_services + supported_text_services}")
        
        return result

    def get_chatbot_response(self, prompt:str, service:str = None, model:str = None, temperature:float = None) -> str:
        service = self.chatbot_service if service is None else service
        model = self.chatbot_model if model is None else model
        temperature = self.chatbot_temperature if temperature is None else temperature

        supported_chatbot_services = ['openai', 'test', 'ollama']

        result = ""
        if service == 'openai':
            result = self.__get_openai_response(prompt, model=model, temperature=temperature)
        elif service == 'test':
            result = "This is test answer from Waifu. Nya kawaii, senpai!"
        elif service == 'ollama':
            result = self.__get_ollama_response(prompt, model=model, temperature=temperature)
        else:
            raise ValueError(f"{service} servise doesn't supported. Please, use one of the following services: {supported_chatbot_services}")
        
        return result

    def tts_say(self, text:str, service:str = None, voice:str = None, model:str = None) -> None:
        service = self.tts_service if service is None else service
        voice = self.tts_voice if voice is None else voice
        model = self.tts_model if model is None else model

        supported_tts_services = ['google', 'elevenlabs', 'console']

        if service not  in supported_tts_services:
            raise ValueError(f"{service} servise doesn't supported. Please, use one of the following services: {supported_tts_services}")
        
        if service == 'google':
            gTTS(text=text, lang='en', slow=False, lang_check=False).save('output.mp3')
        elif service == 'elevenlabs':
            self.__elevenlabs_generate(text=text, voice=voice, model=model)

        elif service == 'console':
            print('\n\33[7m' + "Waifu:" + '\33[0m' + f' {text}')
            return

        data, fs = sf.read('output.mp3')
        sd.play(data, fs)
        sd.wait()

    def conversation_cycle(self) -> dict:
        user_input = self.get_user_input()

        # If the input is empty or just whitespace, skip this cycle
        if not user_input.strip():
            return {}
        
        response = self.get_chatbot_response(user_input)

        self.tts_say(response)

        return dict(user = user_input, assistant = response)

    def __get_openai_response(self, prompt:str, model:str, temperature:float) -> str:
        self.__add_message('user', prompt)
        messages = self.context + self.message_history

        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature, 
        )
        response = response.choices[0].message["content"]

        self.__add_message('assistant', response)
        self.__update_message_history()

        return response

    def __get_ollama_response(self, prompt: str, model: str, temperature: float) -> str:
        self.__add_message('user', prompt)
        messages = self.context + self.message_history

        response = ollama.chat(
            model=model,
            messages=messages,
            stream=False,
            options={'temperature': temperature}
        )
        response_content = response['message']['content']

        self.__add_message('assistant', response_content)
        self.__update_message_history()

        return response_content

    def __add_message(self, role:str, content:str) -> None:
        self.message_history.append({'role': role, 'content': content})

    def __load_chatbot_data(self, file_name:str = None) -> None:
        file_name = self.chatbot_personality_file if file_name is None else file_name

        with open(file_name, 'r') as f:
            personality = f.read()
        self.context = [{'role': 'system', 'content': personality}]

        if path.isfile('./message_history.txt'):
            with open('message_history.txt', 'r') as f:
                try:
                    self.message_history = load(f)
                except JSONDecodeError:
                    pass

    def __update_message_history(self) -> None:
        with open('message_history.txt', 'w') as f:
                dump(self.message_history, f)

    def __get_text_input(self, service:str) -> str:
        user_input = ""
        if service == 'console':
            user_input = input('\n\33[42m' + "User:" + '\33[0m' + " ")
        return user_input

    def __elevenlabs_generate(self, text:str, voice:str, model:str, filename:str='output.mp3'):
        audio = generate(
                 text=text,
                 voice=voice,
                 model=model
                )
        save(audio, filename)

    def __recognise_speech(self, service:str, duration:float) -> str:
        with self.mic as source:
            print('(Start listening)')
            self.recogniser.adjust_for_ambient_noise(source, duration=duration)
            audio = self.recogniser.listen(source)
            print('(Stop listening)')

            result = ""
            try:
                if service == 'whisper':
                    result = self.__whisper_sr(audio)
                elif service == 'google':
                    result = self.recogniser.recognize_google(audio)
            except Exception as e:
                print(f"Exeption: {e}")
        return result

    def __whisper_sr(self, audio) -> str:
        with open('speech.wav', 'wb') as f:
            f.write(audio.get_wav_data())
            audio_file = open('speech.wav', 'rb')
            transcript = openai.Audio.transcribe(model="whisper-1", file=audio_file)
        return transcript['text']

def main():
    w = Waifu()
    w.initialize(user_input_service='console', 
                 chatbot_service='test', 
                 tts_service='google', output_device=8)

    w.conversation_cycle()

if __name__ == "__main__":
    main()