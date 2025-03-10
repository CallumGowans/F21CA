import json
import time
from tools import tools_map
from prompt import gen_prompt, user_prompt
import QWen_LLM as model1
import DeepSeek_LLM as model2
from tools import get_movie_data_from_database
import azure.cognitiveservices.speech as speechsdk


"""
    Tasks:
        Basic logic of agent,
        Tool functions,
        Template of prompt,
        Initialize of LLM
    Hints!: 
        For the remaining unfinished parts, please complete the TODO section in the code 
"""

mp = model2.ModelProvider()
speech_key = "8nXcYzqKoS2oX8DSZRFl2LSKFIKCMWxRotBt4nbi47DgSipkTyBuJQQJ99BBAClhwhEXJ3w3AAAYACOGYh1X"
service_region = "ukwest"

def recognize_speech():
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_recognition_language = "en-US"

    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    print("Please start talking....")
    result = recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print(f"Recognized text: {result.text}")
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        print("Voice not recognized, please try again.")
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print(f"Recognition cancellation: {cancellation_details.reason}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"Error details: {cancellation_details.error_details}")
    return None

def synthesize_speech(text):
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_synthesis_voice_name = "en-GB-SoniaNeural"
    speech_config.speech_recognition_language = "en-US"

    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)

    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("speech synthesizing completed！")
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print(f"Synthesis cancellation: {cancellation_details.reason}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"error: {cancellation_details.error_details}")

def parse_thoughts(response):
    try:
        thoughts = response.get("thoughts")
        plan = thoughts.get("plan_name")
        reasoning = thoughts.get("reasoning")
        criticism = thoughts.get("criticism")
        observation = thoughts.get("observation")
        return f"plan: {plan}\nreasoning: {reasoning}\ncriticism: {criticism}observation: {observation}"
    except Exception as e:
        print(f"Parse Thoughts Error: {e}")
        return f"{e}"


def agent_execute(query, max_request_time=10):
    chat_history = []
    agent_scratch = ''
    request_time = 1
    while request_time <= max_request_time:
        request_time += 1
        # If the returned result meets the criteria, it will be returned directly

        """
            prompt:
                Task description: The definition/goal of our project
                Tools description: including the what kind ofm tool will be used and the args
                User input: The request of user
                Assistant_msg: LLM self reflection
                Restrictions: on replying to messages
        """
        # print("Previous data: ", agent_scratch)
        prompt = gen_prompt(query, agent_scratch)
        start_time = time.time()
        print(f"{request_time - 1}==========Start calling LLM==========")

        # Call LLM
        """
            input:
                sys_prompt, user_msg, assistant_msg, chat_history...
        """
        response = mp.chat(prompt, chat_history)
        print(response)

        end_time = time.time()
        print(f"{request_time - 1}==========Finish calling LLM========== Running time{end_time - start_time}")

        if not response or not isinstance(response, dict):
            print(f"({request_time - 1})Model call failed, retrying")

        """
        prompt = {
            "action": {
                "action_name": "name1"，
                "action_args": {
                    "arg1": "value1"，
                    "arg2": "value2"
                }
            }，
            "thoughts": {
                "plan_name": "",
                "criticism": "",
                "observation": "",
                "reasoning": ""
            }
        }
        """
        try:
            action_info = response.get("action")
            print(action_info)
            action_name = action_info.get("action_name")
            print(action_name)
            action_args = action_info.get("action_args")
            print(action_args, type(action_args))
            print(f"Current action name: {action_name}, \nargs:{action_args}")

            if action_name == "finish":
                final_answer = action_args.get("answer")
                print(f"Final answer: {final_answer}")
                synthesize_speech(final_answer)
                break
            elif action_name == "off_topic":
                print("Sorry, I can only provide movie recommendation services. Please inquire again")
                break

            observation = response.get("thoughts").get("observation")

            try:
                """
                    Mapping from action_name to functions: map -> {action_name: func)
                """
                # TODO: In this section, complete tools_map to specify the correspondence
                #       between action names and different functions

                if action_name == "get_movie_data_from_database":
                    if isinstance(mp, model2.ModelProvider):
                        action_args = {
                            'query': json.loads(action_args.get('query', '{}'))
                        }
                        # print(f"\033[33mMOVIE DATA CON: {type(action_args)} {action_args}\033[0m")
                        # print(f"\033[33mMOVIE DATA CON1: {type(action_args.get('query'))} {action_args.get('query')}\033[0m")

                    func = tools_map.get(action_name)
                    observation = func(**action_args)

                    print(f"\033[33mConditions: {type(action_args)} {action_args} \033[0m")
                    print(f"\033[33mResult: {observation}\033[0m")
                    if observation and isinstance(observation, list):
                        query = "You have already obtained sufficient data from the database in the previous steps, you cannot called action named “getmovie_data_from_database” again. Based on the movie information contained in 'Movie_datas,' generate a recommendation-style text: Your language should be natural and should not sound AI-generated. Your response should introduce the movies in the first person, such as ‘I want to recommend...’. The tone can be humorous and engaging, with a review-like style, rather than simply listing information. Directly output the movie recommendation text without including any formatting markers (such as Markdown syntax). Finally, return the generated text."



                else:
                    func = tools_map.get(action_name)
                    observation = func(**action_args)
                    print(f"\033[33mConditions: {type(action_args)} {action_args} \nResult: {observation}\033[0m")

            # action_name: func
            except Exception as e:
                print(f"Tool Function Call Error: {e}")

            agent_scratch = action_name + ":" + str(observation) + "\n"

            # temp = response.get("actions").get("action name")
            # user_prompt = f"Deciding which tools to use: {temp}"
            assistant_msg = parse_thoughts(response)
            chat_history.append([user_prompt, assistant_msg])

        except Exception as e:
            print(f"Error: {e}")

        if request_time > max_request_time:
            print("The task has failed, exceeding the maximum number of cycles")
        else:
            print("This task was successful")


def main():
    # main logic of agent
    max_request_time = 10

    print("Current model", type(mp))
    while True:
        print("Movie recommendation system --- Please say your requirements:\n")
        query = recognize_speech()
        if query == 'exit':
            exit()
        agent_execute(query, max_request_time=max_request_time)


if __name__ == '__main__':
    main()
