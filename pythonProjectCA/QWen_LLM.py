import os
from openai import OpenAI
from prompt import user_prompt
import json
from dotenv import load_dotenv
import re

load_dotenv()
# os.environ["OPENAI_API_KEY"] = "sk-e8ed06f1aeaa40fb9865db0f53329ffe"
api_key = os.environ.get("QWEN_OPENAI_API_KEY")


def json_string_to_dict(json_str):
    """
    将多层嵌套的 JSON 字符串转换为字典。
    如果值是可以解析为 JSON 的字符串，递归地将其转换为字典。
    """
    def recursive_parse(data):
        if isinstance(data, dict):
            # 如果是字典，递归处理每个值
            return {key: recursive_parse(value) for key, value in data.items()}
        elif isinstance(data, list):
            # 如果是列表，递归处理每个元素
            return [recursive_parse(item) for item in data]
        elif isinstance(data, str):
            # 如果是字符串，尝试解析为 JSON
            try:
                parsed = json.loads(data)
                # 如果解析成功，递归处理解析后的结果
                return recursive_parse(parsed)
            except json.JSONDecodeError:
                # 如果解析失败，返回原始字符串
                return data
        else:
            # 其他类型（如 int, float, bool）直接返回
            return data

    # 首先将输入的 JSON 字符串解析为 Python 对象
    try:
        parsed_data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"输入的 JSON 字符串格式不正确: {e}")

    # 递归处理解析后的数据
    return recursive_parse(parsed_data)


def extract_json_from_content(content):
    """
    从 content 字段中提取 JSON 数据并解析为字典。
    支持两种格式：
    1. 字符串格式（包含 ```json ``` 代码块）。
    2. 字典格式（直接是字典）。
    """
    if isinstance(content, dict):
        # 如果 content 已经是字典，直接返回
        return content
    elif isinstance(content, str):
        # 如果是字符串，尝试提取 JSON 代码块
        json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
        if json_match:
            # 提取 JSON 字符串
            json_str = json_match.group(1).strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"JSON 解析失败: {e}")
        else:
            # 如果没有代码块，尝试直接解析整个字符串
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"JSON 解析失败: {e}")
    else:
        raise ValueError("content 字段必须是字符串或字典")


class ModelProvider():
    def __init__(self):
        self.client = OpenAI(
            api_key="sk-e8ed06f1aeaa40fb9865db0f53329ffe",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.max_retry_time = 3

    def chat(self, prompt, chat_history):
        for i in range(self.max_retry_time):
            try:
                messages = [{'role': 'system', 'content': prompt}]
                for chat_msg in chat_history:
                    messages.append({'role': 'user', 'content': chat_msg[0]})
                    messages.append({'role': 'assistant', 'content': chat_msg[1]})
                messages.append({'role': 'user', 'content': user_prompt})
                response = self.client.chat.completions.create(
                    model="qwen-plus",
                    messages=messages,
                )

                """
                    {
                    "id":"chatcmpl-aa7cddc7-fdd6-9026-a167-b7012435f079",
                    "choices":[{
                        "finish_reason":"stop",
                        "index":0,
                        "logprobs":null,
                        "message":{
                            "content":"I am a large-scale language model from Alibaba Cloud, and my name is Tongyi Qianwen.",
                            "refusal":null,"role":"assistant",
                            "audio":null,
                            "function_call":null,
                            "tool_calls":null
                        }
                    }],
                    "created":1739020006,
                    "model":"qwen-plus",
                    "object":"chat.completion",
                    "service_tier":null,
                    "system_fingerprint":null,
                    "usage":{
                        "completion_tokens":17,
                        "prompt_tokens":22,
                        "total_tokens":39,
                        "completion_tokens_details":null,
                        "prompt_tokens_details":{
                            "audio_tokens":null,
                            "cached_tokens":0
                        }}
                    }
                """
                response = json_string_to_dict(response.model_dump_json())
                print("Model response: ", response)
                content = response["choices"][0]["message"]["content"]
                print("Model content: ", content, type(content))
                try:
                    result = extract_json_from_content(content).get("prompt")
                    print("\033[36mModel result: ", result, "\033[0m")
                    return result
                except Exception:
                    return content

            except Exception as e:
                print(f"LLM call Failed: {e}")
            return {}
