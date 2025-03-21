import json
from langchain_community.tools.tavily_search import TavilySearchResults


"""
1.Network search
2.Database query
3. ...
"""

# Store information on all tools to help LLM understand their functions
tools_info = [
    {
        "name": "finish",
        "description": "Task complete, gain the final proper result for user's goal",
        "args": [
            {
                "name": "answer",
                "type": "String",
                "description": "The goal's final answer"
            }
        ]
    },
    {
        "name": "off_topic",
        "description": "When the response to the user's request is unrelated to the movie, call this method to guide the user to re initiate the request",
        "args": [
            {
                "name": "None",
                "type": "None",
                "description": "None"
            }
        ]
    },
    # {
    #     "name": "network_search",
    #     "description": "Used for searching specified information online",
    #     "args": [
    #         {
    #             "name": "query",
    #             "type": "String",
    #             "description": "Questions/datas requiring online search"
    #         }
    #     ]
    # },
    #
    #
    # {
    #     "name": "query_movie_data",
    #     "description": "Get movie information, including title, year,genres,directors,cast,rating,synopsis",
    #     "args": [
    #         {
    #             "name": "query",
    #             "type": "String",
    #             "description": "The movie information that the user wants to query "
    #         }
    #     ]
    # }


    # TODO: Fill in information on other tools and methods
]


def network_search(query):
    tavily_result = TavilySearchResults(max_results=5)

    try:
        ret = tavily_result.invoke(input=query)
        """
        ret: 
        [{
            "content": "",
            "urL": ""
        }]
        """
        content_list = [obj['content'] for obj in ret]
        return "\n".join(content_list)

    except Exception as err:
        return "search err: {}".format(err)


def query_movie_data(query):
    # TODO: Using llama_index to complete the return of movie data
    pass

# TODO: Improving the project will provide other tools and methods for LLM to use


tools_map = {
    # "network_search": network_search,
    # "query_movie_data": query_movie_data
}


def gen_tools_description():
    tools_desc = []
    for id, desc in enumerate(tools_info):
        args_desc = []
        for info in desc['args']:
            args_desc.append({
                "name": info["name"],
                "type": info["type"],
                "description": info["description"]
            })
        args_desc = json.dumps(args_desc, ensure_ascii=False)
        desc_text = f"{id + 1}, {desc['name']}: {desc['description']}, args: {args_desc}"
        tools_desc.append(desc_text)
    return "\n".join(tools_desc)
