import requests
import json
import os
from prompt import user_prompt
from dotenv import load_dotenv
from QWen_LLM import  extract_json_from_content

def parse_json(json_str):
    """
    解析 JSON 字符串并返回 Python 字典。
    自动解析嵌套的 JSON 字符串，例如 "query_conditions" 内部的 JSON 数据。
    """
    def recursive_parse(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                obj[key] = recursive_parse(value)
        elif isinstance(obj, list):
            obj = [recursive_parse(item) for item in obj]
        elif isinstance(obj, str):
            try:
                parsed_value = json.loads(obj)  # 尝试解析字符串为 JSON
                return recursive_parse(parsed_value)  # 递归解析内部 JSON
            except json.JSONDecodeError:
                return obj  # 如果解析失败，返回原始字符串
        return obj

    parsed_data = json.loads(json_str)  # 解析最外层 JSON
    return recursive_parse(parsed_data)


load_dotenv()
API_KEY = os.environ.get("DEEPSEEK_API_KEY")
API_URL = os.environ.get("DEEPSEEK_API_URL")


class ModelProvider:
    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        self.max_retry_time = 3
        self.model_name = "deepseek-ai/DeepSeek-V3"

    def chat(self, prompt, chat_history):
        print("DeepSeek model responding...")
        for i in range(self.max_retry_time):
            try:
                messages = [{'role': 'system', 'content': prompt}]
                for chat_msg in chat_history:
                    messages.append({'role': 'user', 'content': chat_msg[0]})
                    messages.append({'role': 'assistant', 'content': chat_msg[1]})

                messages.append({'role': 'user', 'content': prompt})


                data = {
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1500
                }

                response = requests.post(API_URL, headers=self.headers, json=data)

                if response.status_code != 200:
                    print(f"\nAPI Request failed, status code:{response.status_code}")
                    print(f"Error message:{response.text}")
                    return None

                result = response.json()
                print("\033[36mModel response: ", result, "\033[0m")

                if "choices" in result and len(result["choices"]) > 0:
                    response_text = result["choices"][0]["message"]["content"]
                    try:
                        json_start = response_text.find("{")
                        json_end = response_text.rfind("}") + 1

                        if json_start == -1 or json_end == -1:
                            return {
                                "action": {
                                    "action_name": "finish",
                                    "action_args": {"answer": response_text.strip()}
                                }
                            }

                        json_str = response_text[json_start:json_end]
                        content = json.loads(json_str)
                        result = extract_json_from_content(content).get("prompt")
                        return result

                    except json.JSONDecodeError:
                        # Fallback for broken JSON
                        return {
                            "action": {
                                "action_name": "finish",
                                "action_args": {"answer": response_text.strip()}
                            }
                        }

                else:
                    print("\nThe data returned by the API does not contain the expected content")
                    return {}

            except requests.exceptions.RequestException as e:
                print(f"\nAPI Request Exception：{e}")
                return {}
            except json.JSONDecodeError:
                print("\nThe API response content is not valid JSON!")
                return {}