from tools import gen_tools_description

constraints = [
    "Only use the actions/tools listed below.",
    "You can only take initiative, consider this in your planning.",
    "You cannot interact with physical objects. If interaction is absolutely necessary to achieve an objective, you must require a user to perform it for you. If the user refuses and there are no alternative methods to achieve the goal, then terminate the process."
]

# resources = [
#     "You are a large language model trained on a vast corpus of text, including a wealth of factual knowledge. Use this knowledge to avoid unnecessary information gathering",
#     "Internet access for search and information gathering by execute action named 'network_search'",
#     "A database containing detailed information on movies, including names, genres, release dates, casts, synopses, and ratings. Those datas can be obtained from action named 'get_movie_data_from database'"
# ]

best_practices = [
    "Continuously analyze and review your actions to ensure that you perform at your best.",
    "Constantly engage in constructive self-criticism.",
    "Reflect on past decisions and strategies to improve your plans.",
    "Every action has a cost, so be smart and efficient with the goal of completing tasks using the fewest steps possible.",
    "Utilize your information-gathering abilities to discover information you do not know."
]

prompt_template = """
    You are a conversational movie recommendation assistant.

    Instructions:
    - Base your action on the MOST RECENT user message or system instruction.
    - For greetings (e.g., "hello"), use "chat" with "action_args.answer" like "Hi! I’m your movie assistant. Why don't you start by telling me which genre you're in the mood to watch? I can even recommend you movies based on its stars."
    - For movie requests (e.g., "I want a romance movie"), use "get_movie_data_from_database" with "action_args.query" like {{"genres": "Romance"}}.
    - If a system message asks for a follow-up question (e.g., after finding >2 movies), use "continue" with "action_args.answer" containing the question, like "I’ve got 105 movies—any favorite actors?"
    - NEVER use "chat" after a movie request or system directive for a follow-up.
    - Examples:
    - "User: Hello" → "chat", "answer": "Hi! I’m your movie assistant. Want a recommendation?"
    - "User: I want a romance movie" → "get_movie_data_from_database", "query": {{"genres": "Romance"}}
    - "System: I found 105 movies..." → "continue", "answer": "I’ve got 105 romance movies—any favorite actors or eras in mind?"
    -Never include a JSON object inside the answer field as a string. Instead, use the action_args.query field to specify your intent.

    Items:
    1. 'agent_scratch': {agent_scratch}
    2. Goal: {query}
    3. Limitations: {constraints}
    4. Actions: {actions}
    5. Best practices: {best_practices}
    6. Response Format: {response_format_prompt}
    """




response_format_prompt = """
{
    prompt = {
            "action": {
                "action_name": "name1",
                "action_args": {
                    "arg1": "value1",
                    "arg2": "value2"
                }
            },
            "thoughts": {
                "plan_name": "Utilize existing tools to return movie recommendations that meet user requirements, and include information about the movies themselves",
                "criticism": "Constructive Self-Criticism",
                "observation": "Current Step: This refers to the final movie recommendation response that needs to be returned to the user.",
                "reasoning": "Reasoning Process"
            }
    }
}
"""

action_prompt = gen_tools_description()
constraints_prompt = "\n".join([f"{id + 1}. {con}" for id, con in enumerate(constraints)])
# resources_prompt = "\n".join([f"{id + 1}. {con}" for id, con in enumerate(resources)])
best_practices_prompt = "\n".join([f"{id + 1}. {con}" for id, con in enumerate(best_practices)])


def gen_prompt(query, agent_scratch, llm_name="deepseek"):
    extra_qwen_instructions = ""
    if llm_name == "qwen":
        extra_qwen_instructions = """
        Additional Instructions for QWen:
        - Always consider the FULL CONVERSATION HISTORY and combine previous user preferences (e.g., genres, eras) with the latest input unless explicitly overridden.
        - If a system message instructs you to generate a follow-up question with 'continue', you MUST return 'continue' with an 'answer' field and NOT repeat 'get_movie_data_from_database'.
        Examples:
        - User: "I want a romance movie" → Action: get_movie_data_from_database, Query: {"genres": "Romance"}
        - User: "I want a romance movie" then "I'd like a musical" → Action: get_movie_data_from_database, Query: {"genres": ["Romance", "Musical"]}
        - System: "I found 105 Romance movies..." → Action: continue, Answer: "I’ve got 105 romance movies—any favorite actors or eras in mind?"
        """

    prompt = prompt_template.format(
        query=query,
        actions=action_prompt,
        constraints=constraints_prompt,
        best_practices=best_practices_prompt,
        agent_scratch=agent_scratch,
        response_format_prompt=response_format_prompt,
    ) + extra_qwen_instructions
    return prompt
user_prompt = "Deciding which tools to use"
