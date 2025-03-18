import json
import time
from tools import tools_map
from prompt import gen_prompt
import DeepSeek_LLM as model2
import azure.cognitiveservices.speech as speechsdk

class MovieAgent:
    def __init__(self):
        self.chat_history = []
        self.agent_scratch = ''
        self.mp = model2.ModelProvider()
        self.speech_key = "YOUR_SPEECH_KEY"
        self.service_region = "YOUR_REGION"

    def recognize_speech(self):
        speech_config = speechsdk.SpeechConfig(subscription=self.speech_key, region=self.service_region)
        speech_config.speech_recognition_language = "en-US"
        audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        print("Please start talking....")
        result = recognizer.recognize_once()
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text
        return None

    def synthesize_speech(self, text):
        speech_config = speechsdk.SpeechConfig(subscription=self.speech_key, region=self.service_region)
        speech_config.speech_synthesis_voice_name = "en-GB-SoniaNeural"
        audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        synthesizer.speak_text_async(text).get()

    def agent_execute(self, query, max_turns=5):
        self.chat_history.append({"role": "user", "content": query})

        for turn in range(max_turns):
            full_conversation = "\n".join(
                [f"{msg['role'].capitalize()}: {msg['content']}" for msg in self.chat_history]
            )

            prompt = gen_prompt(full_conversation, self.agent_scratch)
            response = self.mp.chat(prompt, [])

            if not response or not isinstance(response, dict):
                return "Sorry, I encountered an issue. Please try again."

            action_info = response.get("action")
            action_name = action_info.get("action_name")
            action_args = action_info.get("action_args")

            if action_name == "finish":
                final_answer = action_args.get("answer")
                self.chat_history.append({"role": "assistant", "content": final_answer})
                return final_answer

            elif action_name == "off_topic":
                reply = "I'm your movie recommendation assistant! Let's stick to movie topics."
                self.chat_history.append({"role": "assistant", "content": reply})
                return reply

            elif action_name == "get_movie_data_from_database":
                query_json = json.loads(action_args.get('query', '{}'))
                movies_data = tools_map["get_movie_data_from_database"](query_json)

                if not movies_data:
                    reply = "I couldn't find movies matching your preferences. Could you specify differently?"
                    self.chat_history.append({"role": "assistant", "content": reply})
                    return reply

                # Save fetched movies explicitly
                self.agent_scratch = json.dumps({"Movie_datas": movies_data})

                # Continue immediately to get a recommendation based on fetched movies
                query = ("You've retrieved the requested movie data. "
                        "Based on 'Movie_datas', provide a conversational, engaging movie recommendation. "
                        "Avoid robotic language, keep it natural.")
                self.chat_history.append({"role": "user", "content": query})

            else:
                reply = "I'm not sure I understood. Could you clarify what movie you'd like?"
                self.chat_history.append({"role": "assistant", "content": reply})
                return reply

        return "I'm sorry, I'm having trouble providing a recommendation right now."
