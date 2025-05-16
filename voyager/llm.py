import logging
import os
import time
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)


class ChatOpenRouter(ChatOpenAI):
    openai_api_base: str
    openai_api_key: str
    model_name: str

    def __init__(self,
                 model_name: str,
                 api_key: Optional[str] = None,
                 base_url: str = "https://openrouter.ai/api/v1",
                 **kwargs):
        api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        super().__init__(base_url=base_url,
                         api_key=api_key,
                         model_name=model_name, **kwargs)


def create_llm(
        model_name,
        temperature,
        request_timeout,
) -> BaseChatModel:
    if model_name.startswith("gpt"):
        model = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            request_timeout=request_timeout,
            max_retries=10,
        )
    elif model_name.startswith("o3") or model_name.startswith("o1"):
        model = ChatOpenAI(
            model_name=model_name,
            request_timeout=request_timeout,
            max_retries=10,
        )
    elif model_name.startswith("deepseek"):
        model = ChatDeepSeek(
            model_name=model_name,
            temperature=temperature,
            request_timeout=request_timeout,
            max_retries=10,
        )
    elif model_name.startswith("ollama-"):
        model = ChatOllama(
            model=model_name[7:],
            base_url="host.docker.internal",
            temperature=temperature,
            request_timeout=request_timeout,
            max_retries=10,
            num_ctx=16382,
        )
    elif model_name.startswith("openrouter-"):
        model = ChatOpenAI(
            model_name=model_name[11:],
            temperature=temperature,
            request_timeout=request_timeout,
            max_retries=10,
            api_key=os.getenv('OPENROUTER_API_KEY'),
            base_url="https://openrouter.ai/api/v1",
        )
    else:
        raise ValueError(f"Unknown model name: {model_name}")

    return model


def invoke_with_log(model: BaseChatModel, messages, *args, prefix="", **kwargs):
    model_name = model.model_name
    if model_name.startswith("o3") or model_name.startswith("o1") or model_name.startswith("openrouter-o3"):
        # Replace system messages with developer messages
        for i, message in enumerate(messages):
            if isinstance(message, SystemMessage):
                messages[i] = {"role": "developer", "content": message.content}
            elif isinstance(message, dict) and message.get("role") == "system":
                messages[i] = {"role": "developer", "content": message.get("content")}

    # Start measuring time
    start_time = time.time()

    # Call the original invoke method
    response = model.invoke(messages, *args, **kwargs)

    # Calculate elapsed time
    elapsed_time = time.time() - start_time

    # Log the time taken and token usage (assuming 'usage' key contains token info)
    logger.info(f"{prefix}AI invoke: response time: {elapsed_time:.2f}s, usage metadata: {response.usage_metadata}")

    return response
