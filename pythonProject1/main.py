import json
import time
from tools import tools_map
from prompt import gen_prompt, user_prompt
import tongyi_test_model as model

"""
    Tasks:
        Basic logic of agent,
        Tool functions,
        Template of prompt,
        Initialize of LLM
    Hints!: 
        For the remaining unfinished parts, please complete the TODO section in the code 
"""

mp = model.ModelProvider()


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
    request_time = 0
    while request_time < max_request_time:
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
        prompt = gen_prompt(query, agent_scratch)
        start_time = time.time()
        print(f"{request_time}==========Start calling LLM==========")

        # Call LLM
        """
            input:
                sys_prompt, user_msg, assistant_msg, chat_history...
        """
        response = mp.chat(prompt, chat_history)
        print(response)

        end_time = time.time()
        print(f"{request_time}==========Finish calling LLM========== Running time{end_time - start_time}")

        if not response or not isinstance(response, dict):
            print(f"({request_time})Model call failed, retrying")

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

        action_info = response.get("action")
        print(action_info)
        action_name = action_info.get("action_name")
        print(action_name)
        action_args = action_info.get("action_args")
        print(action_args)
        print(f"Current action name:{action_name}, args:{action_args}")

        if action_name == "finish":
            final_answer = action_args.get("answer")
            print(f"Final answer:{final_answer}")
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

            func = tools_map.get(action_name)
            observation = func(**action_args)

        # action_name: func
        except Exception as e:
            print(f"Tool Function Call Error: {e}")

        agent_scratch = agent_scratch + "\n" + observation

        # temp = response.get("actions").get("action name")
        # user_prompt = f"Deciding which tools to use: {temp}"
        assistant_msg = parse_thoughts(response)
        chat_history.append([user_prompt, assistant_msg])
    if request_time == max_request_time:
        print("The task has failed, exceeding the maximum number of cycles")
    else:
        print("This task was successful")


def main():
    # main logic of agent
    max_request_time = 10
    while True:
        query = input("Movie recommendation system --- Please enter your requirements:\n")
        if query == 'exit':
            exit()
        agent_execute(query, max_request_time=max_request_time)


if __name__ == '__main__':
    main()
