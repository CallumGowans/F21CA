import json
from langchain_community.tools.tavily_search import TavilySearchResults
import sqlite3
from typing import Union

"""
1.Network search
2.Database query
3. ...
"""

# Store information on all tools to help LLM understand their functions
tools_info = [
    {
        "name": "finish",
        "description": "Task complete, Generate a movie recommendation text for user's goal by using the data provided by 'Movie_datas'",
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

    {
        "name": "get_movie_data_from_database",
        "description": "Fetch movie data (title/year/genres/directors/cast/rating/synopsis) from the database using flexible filters including exact or range queries.",
        "args": [
            {
                "name": "query",
                "type": "JSON String",
                "description":
                    "JSON-formatted query conditions. Supported fields:\n"
                    "1. title      : Movie title (fuzzy match, e.g., \"Inception\")\n"
                    "2. year       : Release year (single value: 2019 or range: [2010,2020])\n"
                    "3. rating     : Minimum rating (single value: 7.0) or rating range: [7.0,9.0]\n"
                    "4. genres     : Genre (fuzzy match, e.g., \"Sci-Fi\")\n"
                    "5. cast       : Actor/Actress (fuzzy match, e.g., \"Tom Cruise\")\n"
                    "6. directors  : Director (fuzzy match, e.g., \"Christopher Nolan\")\n\n"
                    "Examples:\n"
                    "- Single filter: {\"year\": 2019}\n"
                    "- Combined filters: {\"year\": [2010,2020], \"rating\": [7.5,8.5], \"genres\": \"Action\"}\n\n"
                    "Notes:\n"
                    "- Fuzzy matches (title/genres/cast/directors) auto-wrap with `%` wildcards.\n"
                    "- Range values (year/rating) are auto-sorted (e.g., [2020,2010] → [2010,2020]).\n"
                    "- Backward compatible: Single-value queries like {\"rating\": 8.0} still work."
            }
        ]
    }

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


def get_movie_data_from_database(query: dict) -> list[dict]:

    """
    从数据库查询符合条件的电影，支持年份和评分的范围查询。

    :param query:查询条件字典，支持以下键：
        - title (str): 电影标题（模糊匹配）
        - year (int | tuple): 年份，可传单个值（如 2019）或范围（如 (2010, 2020)）
        - rating (float | tuple): 评分，可传单个值（如 7.0）或范围（如 (7.0, 9.0)）
        - genres (str): 类型（模糊匹配）
        - cast (str): 演员（模糊匹配）
        - directors (str): 导演（模糊匹配）
    :return: 电影字典列表，包含字段：title, year, genres, directors, cast, rating, synopsis
    """
    conn = sqlite3.connect("movies.db")
    cursor = conn.cursor()

    # 有效条件过滤
    valid_keys = {"title", "rating", "year", "genres", "cast", "directors"}
    conditions = {k: v for k, v in query.items() if k in valid_keys}

    query = """
    SELECT title, year, genres, directors, "cast", rating, synopsis 
    FROM movies 
    WHERE 1=1
    """
    params = []

    # 字段处理逻辑
    def _handle_range(field: str, value: Union[int, float, tuple]) -> tuple[str, list]:
        if isinstance(value, (tuple, list)):
            if len(value) != 2:
                raise ValueError(f"{field}范围值需要两个元素")
            start, end = sorted(value)  # 自动排序确保 start <= end
            return f" AND {field} BETWEEN ? AND ?", [start, end]
        else:
            # 默认行为：year用等值，rating用 >=
            if field == "year":
                return f" AND {field} = ?", [value]
            else:
                return f" AND {field} >= ?", [value]

    field_handlers = {
        "title": lambda val: (" AND title LIKE ?", [f"%{val}%"]),
        "year": lambda val: _handle_range("year", val),
        "rating": lambda val: _handle_range("rating", val),
        "genres": lambda val: (" AND genres LIKE ?", [f"%{val}%"]),
        "cast": lambda val: (' AND "cast" LIKE ?', [f"%{val}%"]),
        "directors": lambda val: (" AND directors LIKE ?", [f"%{val}%"]),
    }

    for field, value in conditions.items():
        if field not in field_handlers:
            continue
        clause, p = field_handlers[field](value)
        query += clause
        params.extend(p)

    try:
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        movies = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return movies
    except sqlite3.Error as e:
        print(f"数据库错误: {e}")
        conn.close()
        return []
    except ValueError as e:
        print(f"参数错误: {e}")
        return []


# TODO: Improving the project will provide other tools and methods for LLM to use


tools_map = {
    "network_search": network_search,
    "get_movie_data_from_database": get_movie_data_from_database
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