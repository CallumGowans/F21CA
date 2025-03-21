import json
import time
from tools import tools_map
from prompt import gen_prompt
import DeepSeek_LLM as model2
import QWen_LLM as model1
import azure.cognitiveservices.speech as speechsdk

class MovieAgent:
    def __init__(self):
        self.chat_history = []
        self.agent_scratch = ''
        self.use_qwen = False 
        self.model_qwen = model1.ModelProvider()
        self.model_deepseek = model2.ModelProvider()
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
            print("Using Deepseek as LLM")
        elif llm_name == "qwen":
            self.mp = self.model_qwen
            print("Using QWen as LLM")

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
        llm_name = "qwen" if self.mp == self.model_qwen else "deepseek"
        retry_attempts = 3
        wait_time = 5

        for turn in range(max_turns):
            print("iteration: ", turn + 1)
            full_conversation = "\n".join(
                [f"{msg['role'].capitalize()}: {msg['content']}" for msg in self.chat_history]
            )
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
                        if attempt == retry_attempts - 1:
                            return "Sorry, I’ve hit a rate limit with the API. Please try again later!"
                    else:
                        return f"Error: {str(e)}"

            if not response or not isinstance(response, dict):
                return "Sorry, I encountered an issue. Please try again."
            print("Model response: ", response)

            if "choices" in response:
                content = response["choices"][0]["message"]["content"]
                content = content.strip().removeprefix("```json").removesuffix("```")
                try:
                    action_info = json.loads(content)
                    if "prompt" in action_info:
                        action_info = action_info["prompt"]
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
                query_raw = action_args.get('query', {})
                query_json = json.loads(query_raw) if isinstance(query_raw, str) else query_raw
                # Merge with previous query context
                if self.current_query:
                    merged_query = self.current_query.copy()
                    if "genres" in query_json:
                        # Normalize both to lists
                        current_genres = merged_query.get("genres", [])
                        if isinstance(current_genres, str):
                            current_genres = [current_genres]
                        new_genres = query_json["genres"]
                        if isinstance(new_genres, str):
                            new_genres = [new_genres]
                        # Combine and deduplicate genres
                        merged_query["genres"] = list(set(current_genres + new_genres))
                    # Update other fields (e.g., year, rating) if present
                    merged_query.update({k: v for k, v in query_json.items() if k != "genres"})
                    query_json = merged_query
                self.current_query = query_json  # Update current query context

                # Handle genres: if multiple genres, query separately and intersect results
                movies_data = []
                if "genres" in query_json:
                    genres = query_json["genres"]
                    # Ensure genres is a list
                    if isinstance(genres, str):
                        genres = [genre.strip() for genre in genres.split(",")]
                    elif not isinstance(genres, list):
                        genres = [genres]
                    # Map genres to the capitalized form used in the database
                    genre_mapping = {
                        "romance": "Romance",
                        "romantic": "Romance",
                        "musical": "Musical",
                        # Add more mappings as needed
                    }
                    genres = [genre_mapping.get(genre.lower(), genre) for genre in genres]
                    if len(genres) > 1:
                        # Query for each genre separately and intersect results
                        result_sets = []
                        all_movies = []  # Store all movie data to rebuild movies_data later
                        for genre in genres:
                            single_genre_query = query_json.copy()
                            single_genre_query["genres"] = genre  # Keep as a single string, not a list
                            print(f"Querying for genre: {single_genre_query}")
                            try:
                                genre_results = tools_map["get_movie_data_from_database"](single_genre_query)
                                print(f"Results for {genre}: {genre_results}")
                                if not genre_results:
                                    # If any genre returns no results, the intersection will be empty
                                    movies_data = []
                                    break
                                # Store all movies for later use
                                all_movies.extend(genre_results)
                                # Collect titles for intersection
                                result_sets.append(set(movie["title"] for movie in genre_results))
                            except Exception as e:
                                print(f"Error querying for genre {genre}: {str(e)}")
                                movies_data = []
                                break
                        if result_sets:
                            try:
                                # Intersect all result sets to find movies that match all genres
                                common_titles = set.intersection(*result_sets)
                                print(f"Common titles after intersection: {common_titles}")
                                # Rebuild movies_data using all_movies, ensuring we include all matching movies
                                movies_data = [
                                    movie for movie in all_movies
                                    if movie["title"] in common_titles
                                ]
                                # Remove duplicates (since all_movies may contain the same movie multiple times)
                                seen_titles = set()
                                unique_movies_data = []
                                for movie in movies_data:
                                    if movie["title"] not in seen_titles:
                                        seen_titles.add(movie["title"])
                                        unique_movies_data.append(movie)
                                movies_data = unique_movies_data
                            except Exception as e:
                                print(f"Error during intersection: {str(e)}")
                                movies_data = []
                    else:
                        # Single genre, query directly
                        query_json["genres"] = genres[0] if genres else ""  # Ensure it's a string
                        print("Database query: ", query_json)
                        try:
                            movies_data = tools_map["get_movie_data_from_database"](query_json)
                        except Exception as e:
                            print(f"Error querying database: {str(e)}")
                            movies_data = []
                else:
                    # No genres, query directly
                    print("Database query: ", query_json)
                    try:
                        movies_data = tools_map["get_movie_data_from_database"](query_json)
                    except Exception as e:
                        print(f"Error querying database: {str(e)}")
                        movies_data = []

                print("Movies data returned: ", movies_data)
                if not movies_data:
                    reply = "I couldn't find movies matching your preferences. Could you specify differently?"
                    self.chat_history.append({"role": "assistant", "content": reply})
                    return reply
                
                self.agent_scratch = json.dumps({"Movie_datas": movies_data, "movie_count": len(movies_data)})
                movie_count = len(movies_data)
                print("Number of movies found is:", movie_count)
                # ... rest of the block remains unchanged ...




                if movie_count > 2:
                    system_query = (
                        f"I found {movie_count} {query_json.get('genres', '')} movies. "
                        "Generate a warm, natural follow-up question to refine the list based on the user's input. "
                        "For example: 'I found 105 romance movies—wow, that’s a lot! Let’s narrow it down. "
                        "Would you like a comedy romance, a musical, or something else?' "
                        "You MUST return 'continue' with a follow-up question here—do not repeat 'get_movie_data_from_database' since the data is already fetched. "
                        "Return a JSON object with 'action_name': 'continue' and 'answer': '<your question>'. "
                        "Example: {'action_name': 'continue', 'answer': 'I found 5 action movies—do you want fast-paced or suspenseful?'}"
                    )
                    self.chat_history.append({"role": "system", "content": system_query})
                    full_conversation = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in self.chat_history])
                    scratch_summary = f"movie_count: {movie_count}, genres: {query_json.get('genres', '')}"
                    prompt = f"Latest User Input: {query}\n\n" + gen_prompt(full_conversation, scratch_summary, llm_name)
                    print("Prompt sent to LLM: ", prompt)

                    for attempt in range(retry_attempts):
                        try:
                            response = self.mp.chat(prompt, [])
                            print("Raw LLM response: ", response)
                            break
                        except Exception as e:
                            if "429" in str(e):
                                print(f"Rate limit hit (attempt {attempt + 1}/{retry_attempts}). Waiting {wait_time} seconds...")
                                time.sleep(wait_time)
                                wait_time *= 2
                            else:
                                return f"Error: {str(e)}"

                    print("Debug: Full response from LLM: ", response)
                    if response is None or not isinstance(response, dict):
                        reply = f"I found {movie_count} movies—can you give me more to work with?"
                        self.chat_history.append({"role": "assistant", "content": reply})
                        print("Debug: Returning fallback due to invalid response: ", reply)
                        return reply

                    if "choices" in response:  # Raw API response
                        content = response["choices"][0]["message"]["content"].strip()
                        print("Debug: Raw content: ", content)
                        if content.startswith("```json"):
                            content = content.removeprefix("```json").removesuffix("```").strip()
                            print("Debug: Stripped content: ", content)
                        try:
                            action_info = json.loads(content)
                            print("Debug: Parsed action_info: ", action_info)
                            if "prompt" in action_info:
                                action_data = action_info["prompt"]["action"]
                                print("Debug: Extracted action_data from prompt: ", action_data)
                            else:
                                action_data = action_info["action"]
                                print("Debug: Extracted action_data directly: ", action_data)
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}, Raw content: {content}")
                            reply = f"I found {movie_count} movies—can you give me more to work with?"
                            self.chat_history.append({"role": "assistant", "content": reply})
                            print("Debug: Returning fallback due to JSON error: ", reply)
                            return reply
                    else:  # Processed response from LLM
                        action_data = response.get("action", {})
                        print("Debug: Using action_data from processed response: ", action_data)

                    action_name = action_data.get("action_name")
                    reply = action_data.get("action_args", {}).get("answer")
                    print(f"Debug: action_name={action_name}, reply={reply}")
                    if action_name == "continue" and reply:
                        self.chat_history.append({"role": "assistant", "content": reply})
                        print("Debug: Returning reply: ", reply)
                        return reply
                    else:
                        print(f"Unexpected action_name or missing answer: {action_data}")
                        reply = f"I found {movie_count} movies—can you give me more to work with?"
                        self.chat_history.append({"role": "assistant", "content": reply})
                        print("Debug: Returning fallback: ", reply)
                        return reply
                else:
                    query = (
                        "You’ve retrieved the requested movie data. "
                        "Based on 'Movie_datas', provide a conversational, engaging movie recommendation..."
                    )
                    self.chat_history.append({"role": "user", "content": query})
                    prompt = gen_prompt(full_conversation, self.agent_scratch, llm_name)
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