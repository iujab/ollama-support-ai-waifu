from waifu import Waifu

def main():
    waifu = Waifu()

    waifu.initialize(user_input_service='google',
                    stt_duration = 2,
                    mic_index = 1,

                    chatbot_service='ollama',
                    chatbot_model = 'mistral',
                    chatbot_temperature = 0.7,
                    personality_file = 'personality.txt',

                    tts_service='google', 
                    output_device=9,
                    tts_voice='Rebecca - wide emotional range',
                    tts_model = None
                    )

    while True:
        waifu.conversation_cycle()

if __name__ == "__main__":
    main()