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
        self.speech_key = "N2lCM4E8tLjJAzdnkJWOAkHGzDZQrCro1UzcwVChmJvVs7Wi3r7yJQQJ99BCAClhwhEXJ3w3AAAYACOGsDIF"
        self.service_region = "ukwest"

    def agent_reset(self):
        self.chat_history.clear()
        self.agent_scratch = ''

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
        iteration = 1

        for turn in range(max_turns):
            print("iteration: ", iteration)
            iteration += 1
            full_conversation = "\n".join(
                [f"{msg['role'].capitalize()}: {msg['content']}" for msg in self.chat_history]
            )

            prompt = gen_prompt(full_conversation, self.agent_scratch) + (
                "\nFor standalone greetings like 'hello', 'hi', or 'hey' (without additional context), respond with 'action_name': 'chat' "
                "and include a friendly greeting in 'action_args' under 'answer', e.g., 'Hello! I’m your movie recommendation assistant. How can I help you today?' "
                "\nIf the user mentions anything movie-related (e.g., 'I want to watch a romantic movie', 'horror', 'modern'), immediately use 'action_name': 'get_movie_data_from_database' "
                "with a query based on their request, even if it’s the first message. Do not greet unless explicitly asked or if the input is purely a greeting."
                "\nWhen refining a query, combine all prior filters (e.g., genre, year) from the chat history with new user input "
                "to ensure the query reflects the full context."
            )
            retry_attempts = 3
            wait_time = 5

            for attempt in range(retry_attempts):
                try:
                    response = self.mp.chat(prompt, [])
                    break
                except Exception as e:
                    if "429" in str(e):
                        print(f"Rate limit hit (attempt {attempt + 1}/{retry_attempts}). Waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                        wait_time *= 2
                        if attempt == retry_attempts - 1:
                            return "Sorry, I’ve hit a rate limit with the API. Please try again later!"
                    else:
                        return f"Error: {str(e)}"

            time.sleep(1)
            if not response or not isinstance(response, dict):
                return "Sorry, I encountered an issue. Please try again."

            print("Model response: ", response)

            if "choices" in response:
                content = response["choices"][0]["message"]["content"]
                try:
                    action_info = json.loads(content)
                    action_name = action_info.get("action", {}).get("action_name")
                    action_args = action_info.get("action", {}).get("action_args", {})
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    action_name = "None"
                    action_args = {}
            else:
                action_info = response.get("action", {})
                action_name = action_info.get("action_name")
                action_args = action_info.get("action_args", {})

            if action_name == "finish":
                final_answer = action_args.get("answer")
                self.chat_history.append({"role": "assistant", "content": final_answer})
                return final_answer
            elif action_name == "off_topic":
                reply = "I'm your movie recommendation assistant! Let's stick to movie topics."
                self.chat_history.append({"role": "assistant", "content": reply})
                return reply
            elif action_name == "chat" or action_name == "None":
                final_answer = action_args.get("answer")
                if not final_answer and "choices" in response:
                    final_answer = response["choices"][0]["message"]["content"]
                if not final_answer:
                    final_answer = "Hello! I’m your movie recommendation assistant. How can I help you today?"
                self.chat_history.append({"role": "assistant", "content": final_answer})
                return final_answer
            elif action_name == "get_movie_data_from_database":
                query_json = json.loads(action_args.get('query', '{}'))
                print("Database query: ", query_json)
                movies_data = tools_map["get_movie_data_from_database"](query_json)
                if not movies_data:
                    reply = "I couldn't find movies matching your preferences. Could you specify differently?"
                    self.chat_history.append({"role": "assistant", "content": reply})
                    return reply
                self.agent_scratch = json.dumps({"Movie_datas": movies_data, "movie_count": len(movies_data)})
                movie_count = len(movies_data)
                print("Number of movies found is:", movie_count)
                if movie_count > 2:
                    system_query = (
                        f"I found {movie_count} movies matching your request. "
                        "Please generate a natural, conversational follow-up question to narrow it down, "
                        "based on the current chat history and movie data in 'agent_scratch'. "
                        "Include the number of movies found ({movie_count}) in the question itself to inform the user, "
                        "e.g., 'I’ve got {movie_count} movies here—do you want something action-packed or more chill?' "
                        "Ask about details like genre, actors, directors, years, or themes, and make it engaging! "
                        "Return the question in the 'answer' field with action_name 'continue'."
                    )
                    self.chat_history.append({"role": "system", "content": system_query})
                    full_conversation = "\n".join(
                        [f"{msg['role'].capitalize()}: {msg['content']}" for msg in self.chat_history]
                    )
                    prompt = gen_prompt(full_conversation, self.agent_scratch)
                    for attempt in range(retry_attempts):
                        try:
                            response = self.mp.chat(prompt, [])
                            break
                        except Exception as e:
                            if "429" in str(e):
                                print(f"Rate limit hit (attempt {attempt + 1}/{retry_attempts}). Waiting {wait_time} seconds...")
                                time.sleep(wait_time)
                                wait_time *= 2
                            else:
                                return f"Error: {str(e)}"
                    if "choices" in response:
                        content = response["choices"][0]["message"]["content"]
                        try:
                            action_info = json.loads(content)
                            reply = action_info.get("action", {}).get("action_args", {}).get("answer")
                            if not reply:
                                reply = f"I found {movie_count} movies—can you give me more to work with, like a genre or actor?"
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error in narrowing: {e}")
                            reply = content
                    else:
                        reply = response.get("action", {}).get("action_args", {}).get("answer", f"I found {movie_count} movies—can you give me more to work with, like a genre or actor?")
                    self.chat_history.append({"role": "assistant", "content": reply})
                    return reply
                else:
                    query = (
                        "You’ve retrieved the requested movie data. "
                        "Based on 'Movie_datas', provide a conversational, engaging movie recommendation..."
                    )
                    self.chat_history.append({"role": "user", "content": query})
                    prompt = gen_prompt(full_conversation, self.agent_scratch)
                    response = self.mp.chat(prompt, [])
                    final_answer = response.get("action", {}).get("action_args", {}).get("answer", "Here’s a suggestion...")
                    self.chat_history.append({"role": "assistant", "content": final_answer})
                    return final_answer
            elif action_name == "continue":
                reply = action_args.get("answer", "Hmm, let’s try that again—what kind of movie are you feeling?")
                self.chat_history.append({"role": "assistant", "content": reply})
                return reply
            else:
                reply = "I’m not sure I understood. Could you clarify what movie you’d like?"
                self.chat_history.append({"role": "assistant", "content": reply})
                return reply

        return "I'm sorry, I'm having trouble providing a recommendation right now."