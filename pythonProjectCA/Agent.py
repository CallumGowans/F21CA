import json
import time
import random
from tools import tools_map
from prompt import gen_prompt
import DeepSeek_LLM as model2
import ChatGPT_LLM as model1
import azure.cognitiveservices.speech as speechsdk

class MovieAgent:
    def __init__(self):
        self.chat_history = []
        self.agent_scratch = ''
        self.model_chatgpt = model1.ModelProvider()
        self.model_deepseek = model2.ModelProvider()
        self.current_llm = "deepseek"
        self.mp = self.model_deepseek
        self.speech_key = "N2lCM4E8tLjJAzdnkJWOAkHGzDZQrCro1UzcwVChmJvVs7Wi3r7yJQQJ99BCAClhwhEXJ3w3AAAYACOGsDIF"
        self.service_region = "ukwest"
        self.current_query = {}  # Track ongoing query context

    def agent_reset(self):
        self.chat_history.clear()
        self.agent_scratch = ''
        self.current_query = {}

    def set_llm(self, llm_name):
        if llm_name == "deepseek":
            self.mp = self.model_deepseek
            self.current_llm = "deepseek"
            print("Using Deepseek as LLM")
        elif llm_name == "chatgpt":
            self.mp = self.model_chatgpt
            self.current_llm = "chatgpt"
            print("Using ChatGPT as LLM")

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

    def parse_llm_response(self, response):
        if not response or not isinstance(response, dict):
            return None, None

        if "choices" in response:
            content = response["choices"][0]["message"]["content"].strip()
            if content.startswith("```json"):
                content = content.removeprefix("```json").removesuffix("```").strip()
            try:
                parsed = json.loads(content)
                action = parsed.get("prompt", {}).get("action") or parsed.get("action")
                return action.get("action_name"), action.get("action_args", {})
            except Exception as e:
                print("Failed to parse LLM response:", e)
                return None, None
        else:
            action = response.get("action")
            return action.get("action_name"), action.get("action_args", {})

    def agent_execute(self, query, max_turns=5):
        self.chat_history.append({"role": "user", "content": query})
        llm_name = self.current_llm
        retry_attempts = 3
        wait_time = 5
        pool_size = 0

        for turn in range(max_turns):
            print("iteration:", turn + 1)
            full_conversation = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in self.chat_history])
            scratch_summary = self.agent_scratch if self.agent_scratch else "No prior data"
            prompt = f"Latest User Input: {query}\n\n" + gen_prompt(full_conversation, scratch_summary, llm_name)

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

            action_name, action_args = self.parse_llm_response(response)

            if action_name == "finish":
                answer = action_args.get("answer")
                self.chat_history.append({"role": "assistant", "content": answer})
                return answer

            elif action_name == "off_topic":
                reply = "I'm your movie recommendation assistant! Let's stick to movie topics."
                self.chat_history.append({"role": "assistant", "content": reply})
                return reply

            elif action_name in ("chat", None):
                answer = action_args.get("answer") or "Hello! I’m your movie recommendation assistant. How can I help you today?"
                self.chat_history.append({"role": "assistant", "content": answer})
                return answer

            elif action_name == "get_movie_data_from_database":
                query_raw = action_args.get('query', {})
                query_json = json.loads(query_raw) if isinstance(query_raw, str) else query_raw
                if query_json == self.current_query:
                    reply = "I’ve already searched for those filters. Want to try different genres, years, or actors?"
                    self.chat_history.append({"role": "assistant", "content": reply})
                    return reply

                self.current_query = query_json
                genres = query_json.get("genres")
                if isinstance(genres, str):
                    genres = [g.strip() for g in genres.split(",")]
                elif not isinstance(genres, list):
                    genres = [genres]

                movies_data = []
                result_sets = []
                all_movies = []

                for genre in genres:
                    temp_query = query_json.copy()
                    temp_query["genres"] = genre
                    try:
                        result = tools_map["get_movie_data_from_database"](temp_query)
                        if not result:
                            movies_data = []
                            break
                        result_sets.append(set(m["title"] for m in result))
                        all_movies.extend(result)
                    except Exception as e:
                        print("DB query error:", e)
                        movies_data = []
                        break

                if result_sets:
                    common_titles = set.intersection(*result_sets)
                    movies_data = [m for m in all_movies if m["title"] in common_titles]

                if not movies_data:
                    reply = "I couldn't find any matches. Try adjusting the genre, year, or actors."
                    self.chat_history.append({"role": "assistant", "content": reply})
                    return reply
                pool_size = min(len(movies_data), 20)
                print("****Movie pool size: ", min(len(movies_data), 20))
                self.agent_scratch = json.dumps({
                    "Movie_datas": random.sample(movies_data, pool_size) if len(movies_data) > 2 else movies_data,
                    "movie_count": len(movies_data),
                    "Genres_searched": genres
                })

                # Always insert or replace the system message
                self.chat_history = [msg for msg in self.chat_history if msg["role"] != "system"]
                if len(movies_data) > 2:
                    system_msg = (
                        f"I found {len(movies_data)} {'/'.join(genres)} movies. "
                        "You MUST now suggest 2 from 'Movie_datas' with a short description. "
                        "Then ask 2-3 clarifying questions to narrow down preferences (e.g., actor, director, tone). "
                        "Return JSON like this: {\"action_name\": \"continue\", \"answer\": \"<your message>\"}"
                    )
                    self.chat_history.append({"role": "system", "content": system_msg})

                full_conversation = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in self.chat_history])
                prompt = f"Latest User Input: {query}\n\n" + gen_prompt(full_conversation, self.agent_scratch, llm_name)

                response = self.mp.chat(prompt, [])
                action_name, action_args = self.parse_llm_response(response)

                if action_name in ("continue", "finish"):
                    reply = action_args.get("answer")
                    self.chat_history.append({"role": "assistant", "content": reply})
                    return reply
                else:
                    fallback = f"I found {len(movies_data)} movies. Want to filter by actor, era, or something else?"
                    self.chat_history.append({"role": "assistant", "content": fallback})
                    return fallback

            elif action_name == "continue":
                reply = action_args.get("answer", "Could you clarify what you’re looking for?")
                self.chat_history.append({"role": "assistant", "content": reply})
                return reply

            else:
                fallback = "I’m not sure I understood that. Want to try again with a genre or actor?"
                self.chat_history.append({"role": "assistant", "content": fallback})
                return fallback
