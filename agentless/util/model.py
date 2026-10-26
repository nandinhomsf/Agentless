import collections
import json
import os
import re
import threading
import time
from abc import ABC, abstractmethod
from typing import List

from agentless.util.api_requests import (
    create_anthropic_config,
    create_chatgpt_config,
    num_tokens_from_messages,
    request_anthropic_engine,
    request_chatgpt_engine,
)


class DecoderBase(ABC):
    def __init__(
        self,
        name: str,
        logger,
        batch_size: int = 1,
        temperature: float = 0.8,
        max_new_tokens: int = 1024,
    ) -> None:
        logger.info("Initializing a decoder model: {} ...".format(name))
        self.name = name
        self.logger = logger
        self.batch_size = batch_size
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens

    @abstractmethod
    def codegen(
        self, message: str, num_samples: int = 1, prompt_cache: bool = False
    ) -> List[dict]:
        pass

    @abstractmethod
    def is_direct_completion(self) -> bool:
        pass

    def __repr__(self) -> str:
        return self.name

    def __str__(self) -> str:
        return self.name


class OpenAIChatDecoder(DecoderBase):
    def __init__(self, name: str, logger, **kwargs) -> None:
        super().__init__(name, logger, **kwargs)

    def codegen(
        self, message: str, num_samples: int = 1, prompt_cache: bool = False
    ) -> List[dict]:
        if self.temperature == 0:
            assert num_samples == 1
        batch_size = min(self.batch_size, num_samples)

        config = create_chatgpt_config(
            message=message,
            max_tokens=self.max_new_tokens,
            temperature=self.temperature,
            batch_size=batch_size,
            model=self.name,
        )
        ret = request_chatgpt_engine(config, self.logger)
        if ret:
            responses = [choice.message.content for choice in ret.choices]
            completion_tokens = ret.usage.completion_tokens
            prompt_tokens = ret.usage.prompt_tokens
        else:
            responses = [""]
            completion_tokens = 0
            prompt_tokens = 0

        # The nice thing is, when we generate multiple samples from the same input (message),
        # the input tokens are only charged once according to openai API.
        # Therefore, we assume the request cost is only counted for the first sample.
        # More specifically, the `prompt_tokens` is for one input message,
        # and the `completion_tokens` is the sum of all returned completions.
        # Therefore, for the second and later samples, the cost is zero.
        trajs = [
            {
                "response": responses[0],
                "usage": {
                    "completion_tokens": completion_tokens,
                    "prompt_tokens": prompt_tokens,
                },
            }
        ]
        for response in responses[1:]:
            trajs.append(
                {
                    "response": response,
                    "usage": {
                        "completion_tokens": 0,
                        "prompt_tokens": 0,
                    },
                }
            )
        return trajs

    def is_direct_completion(self) -> bool:
        return False


class AnthropicChatDecoder(DecoderBase):
    def __init__(self, name: str, logger, **kwargs) -> None:
        super().__init__(name, logger, **kwargs)

    _STR_REPLACE_EDITOR_DESCRIPTION = """Custom editing tool for editing files
* State is persistent across command calls and discussions with the user

Notes for using the `str_replace` command:
* The `old_str` parameter should match EXACTLY one or more consecutive lines from the original file. Be mindful of whitespaces!
* If the `old_str` parameter is not unique in the file, the replacement will not be performed. Make sure to include enough context in `old_str` to make it unique
* The `new_str` parameter should contain the edited lines that should replace the `old_str`
"""

    _USER_REPLY_EDIT_MESSAGE = """File is successfully edited"""

    tools = [
        {
            "name": "str_replace_editor",
            "description": _STR_REPLACE_EDITOR_DESCRIPTION,
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "description": "Full path to file, e.g. `folder/file.py`.",
                        "type": "string",
                    },
                    "old_str": {
                        "description": "Required parameter containing the string in `path` to replace.",
                        "type": "string",
                    },
                    "new_str": {
                        "description": "Optional parameter containing the new string (if not given, no string will be added).",
                        "type": "string",
                    },
                },
                "required": ["path", "old_str"],
            },
        }
    ]

    MAX_CODEGEN_ITERATIONS = 10

    # specialized codegen with tool
    def codegen_w_tool(
        self, message: str, num_samples: int = 1, prompt_cache: bool = False
    ) -> List[dict]:
        def _build_response_and_extract(response, messages, iter):
            json_response = response.to_dict()

            contains_tool = False
            # formulate the messages
            json_response.pop("id")
            json_response.pop("model")
            json_response.pop("stop_reason")
            json_response.pop("stop_sequence")
            json_response.pop("type")
            json_response.pop("usage")

            messages.append(json_response)

            response_content = []

            for json_message in json_response["content"]:
                if json_message["type"] == "tool_use":
                    contains_tool = True
                    # each tool use requires a response
                    response_content.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": json_message["id"],
                            "content": self._USER_REPLY_EDIT_MESSAGE,
                        }
                    )

            if contains_tool:
                messages.append(
                    {
                        "role": "user",
                        "content": response_content,
                    }
                )
            else:
                if iter == 0:
                    # if the first iteration does not contain the tool, likely the model is doing some CoT for debugging
                    # append encouraging message
                    messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Please generate editing commands to fix the issue",
                                }
                            ],
                        }
                    )
                    contains_tool = True

            return messages, contains_tool

        if self.temperature == 0:
            assert num_samples == 1

        trajs = []
        for _ in range(num_samples):
            self.logger.info(f" === Generating ====")
            # initialized the traj
            traj = {
                "response": [],
                "usage": {
                    "completion_tokens": 0,
                    "prompt_tokens": 0,
                    "cache_creation_token": 0,
                    "cache_read_input_tokens": 0,
                },
            }

            # create the initial config and messages
            messages = [
                {"role": "user", "content": [{"type": "text", "text": message}]}
            ]

            for iteration in range(self.MAX_CODEGEN_ITERATIONS):
                config = create_anthropic_config(
                    message=messages,
                    max_tokens=self.max_new_tokens,
                    temperature=self.temperature,
                    batch_size=1,
                    model=self.name,
                    tools=self.tools,
                )
                ret = request_anthropic_engine(
                    config,
                    self.logger,
                    prompt_cache=True,  # prompt cache should be always true as we at least should query twice
                )

                if ret:
                    # add the response to the traj
                    traj["response"].append([reply.to_dict() for reply in ret.content])

                    # pretty dump the response
                    for reply in ret.content:
                        self.logger.info(json.dumps(reply.to_dict(), indent=2))

                    # update the usage
                    traj["usage"]["completion_tokens"] += ret.usage.output_tokens
                    traj["usage"]["prompt_tokens"] += ret.usage.input_tokens
                    traj["usage"][
                        "cache_creation_token"
                    ] += ret.usage.cache_creation_input_tokens
                    traj["usage"][
                        "cache_read_input_tokens"
                    ] += ret.usage.cache_read_input_tokens

                    messages, contains_tool = _build_response_and_extract(
                        ret, messages, iteration
                    )

                    if not contains_tool:
                        break
                else:
                    assert (
                        False
                    ), "No response from the engine"  # this should not happen

            if ret:
                trajs.append(traj)
            else:
                trajs.append(
                    {
                        "response": "",
                        "usage": {
                            "completion_tokens": 0,
                            "prompt_tokens": 0,
                        },
                    }
                )

        return trajs

    def codegen(
        self, message: str, num_samples: int = 1, prompt_cache: bool = False
    ) -> List[dict]:
        if self.temperature == 0:
            assert num_samples == 1

        trajs = []
        for _ in range(num_samples):
            config = create_anthropic_config(
                message=message,
                max_tokens=self.max_new_tokens,
                temperature=self.temperature,
                batch_size=1,
                model=self.name,
            )
            ret = request_anthropic_engine(
                config, self.logger, prompt_cache=prompt_cache
            )

            if ret:
                trajs.append(
                    {
                        "response": ret.content[0].text,
                        "usage": {
                            "completion_tokens": ret.usage.output_tokens,
                            "prompt_tokens": ret.usage.input_tokens,
                            "cache_creation_token": 0
                            if not prompt_cache
                            else ret.usage.cache_creation_input_tokens,
                            "cache_read_input_tokens": 0
                            if not prompt_cache
                            else ret.usage.cache_read_input_tokens,
                        },
                    }
                )
            else:
                trajs.append(
                    {
                        "response": "",
                        "usage": {
                            "completion_tokens": 0,
                            "prompt_tokens": 0,
                        },
                    }
                )

        return trajs

    def is_direct_completion(self) -> bool:
        return False


class DeepSeekChatDecoder(DecoderBase):
    def __init__(self, name: str, logger, **kwargs) -> None:
        super().__init__(name, logger, **kwargs)

    def codegen(
        self, message: str, num_samples: int = 1, prompt_cache: bool = False
    ) -> List[dict]:
        if self.temperature == 0:
            assert num_samples == 1

        trajs = []
        for _ in range(num_samples):
            config = create_chatgpt_config(
                message=message,
                max_tokens=self.max_new_tokens,
                temperature=self.temperature,
                batch_size=1,
                model=self.name,
            )
            ret = request_chatgpt_engine(
                config, self.logger, base_url="https://api.deepseek.com"
            )
            if ret:
                trajs.append(
                    {
                        "response": ret.choices[0].message.content,
                        "usage": {
                            "completion_tokens": ret.usage.completion_tokens,
                            "prompt_tokens": ret.usage.prompt_tokens,
                        },
                    }
                )
            else:
                trajs.append(
                    {
                        "response": "",
                        "usage": {
                            "completion_tokens": 0,
                            "prompt_tokens": 0,
                        },
                    }
                )

        return trajs

    def is_direct_completion(self) -> bool:
        return False


class OpenAICompatChatDecoder(DecoderBase):
    """Free-tier provider behind an OpenAI-compatible endpoint.

    Free tiers may reject n > 1, so each sample is a separate request, and
    requests are spaced to respect the per-minute limits on requests
    ({prefix}_RPM) and input tokens ({prefix}_TPM, 0 = unlimited).
    Models that inline their reasoning as <thought>...</thought> (e.g. Gemma)
    have it stripped so Agentless only parses the final answer.
    """

    base_url: str
    env_prefix: str
    thought_re = re.compile(r"<thought>.*?</thought>\s*", re.DOTALL)
    _last_request = 0.0
    _token_window = collections.deque()  # [timestamp, input tokens] of last 60s
    _lock = threading.Lock()

    def __init__(self, name: str, logger, **kwargs) -> None:
        super().__init__(name, logger, **kwargs)
        env = lambda key, default=None: os.environ.get(f"{self.env_prefix}_{key}", default)
        self.api_key = env("API_KEY")
        assert self.api_key, f"{self.env_prefix}_API_KEY is not set"
        self.min_interval = 60.0 / float(env("RPM", "10"))
        self.tpm = int(env("TPM", "0"))
        # tiktoken undercounts non-OpenAI tokenizers (Gemma: up to ~1.8x)
        self.token_pad = float(env("TOKEN_PAD", "1.8"))
        self.reasoning_effort = self.default_reasoning_effort(name, env)
        # inlined reasoning counts against max_tokens; leave room for the answer
        self.thinking_headroom = int(env("THINKING_HEADROOM", "0"))

    def default_reasoning_effort(self, name, env):
        return None

    def _throttle(self, prompt_tokens):
        cls = OpenAICompatChatDecoder
        with cls._lock:
            wait = cls._last_request + self.min_interval - time.time()
            if wait > 0:
                time.sleep(wait)
            while self.tpm:
                now = time.time()
                while cls._token_window and cls._token_window[0][0] < now - 60:
                    cls._token_window.popleft()
                used = sum(t for _, t in cls._token_window)
                # a prompt larger than the whole budget goes out on an empty window
                if not cls._token_window or used + prompt_tokens <= self.tpm:
                    break
                time.sleep(cls._token_window[0][0] + 60 - now + 0.5)
            cls._last_request = time.time()
            entry = [cls._last_request, prompt_tokens]
            if self.tpm:
                cls._token_window.append(entry)
            return entry

    def codegen(
        self, message: str, num_samples: int = 1, prompt_cache: bool = False
    ) -> List[dict]:
        if self.temperature == 0:
            assert num_samples == 1

        trajs = []
        for _ in range(num_samples):
            config = create_chatgpt_config(
                message=message,
                max_tokens=self.max_new_tokens + self.thinking_headroom,
                temperature=self.temperature,
                batch_size=1,
                model=self.name,
            )
            if self.reasoning_effort:
                config["reasoning_effort"] = self.reasoning_effort
            window_entry = self._throttle(
                int(self.token_pad * num_tokens_from_messages(message)) + 50
            )
            ret = request_chatgpt_engine(
                config, self.logger, base_url=self.base_url, api_key=self.api_key
            )
            if ret:
                # calibrate the window with the provider's own token count
                window_entry[1] = ret.usage.prompt_tokens or window_entry[1]
                if ret.choices[0].finish_reason == "length":
                    self.logger.info("WARNING: response truncated by max_tokens")
                trajs.append(
                    {
                        "response": self.thought_re.sub(
                            "", ret.choices[0].message.content or ""
                        ),
                        "usage": {
                            "completion_tokens": ret.usage.completion_tokens,
                            "prompt_tokens": ret.usage.prompt_tokens,
                        },
                    }
                )
            else:
                # fail loudly so the instance is retried on resume instead of
                # being saved with an empty response
                raise RuntimeError(f"{self.env_prefix} request failed after all retries")

        return trajs

    def is_direct_completion(self) -> bool:
        return False


class GeminiChatDecoder(OpenAICompatChatDecoder):
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    env_prefix = "GEMINI"

    def __init__(self, name: str, logger, **kwargs) -> None:
        super().__init__(name, logger, **kwargs)
        if not self.reasoning_effort and "GEMINI_THINKING_HEADROOM" not in os.environ:
            self.thinking_headroom = 4096  # Gemma always reasons inline

    def default_reasoning_effort(self, name, env):
        # GPT-4o (used in the paper) does not reason; keep thinking minimal.
        # Gemma models reject this parameter.
        return env("REASONING_EFFORT", "low") if name.startswith("gemini") else None


class NvidiaChatDecoder(OpenAICompatChatDecoder):
    base_url = "https://integrate.api.nvidia.com/v1"
    env_prefix = "NVIDIA"


def make_model(
    model: str,
    backend: str,
    logger,
    batch_size: int = 1,
    max_tokens: int = 1024,
    temperature: float = 0.0,
):
    if backend == "openai":
        return OpenAIChatDecoder(
            name=model,
            logger=logger,
            batch_size=batch_size,
            max_new_tokens=max_tokens,
            temperature=temperature,
        )
    elif backend == "anthropic":
        return AnthropicChatDecoder(
            name=model,
            logger=logger,
            batch_size=batch_size,
            max_new_tokens=max_tokens,
            temperature=temperature,
        )
    elif backend == "deepseek":
        return DeepSeekChatDecoder(
            name=model,
            logger=logger,
            batch_size=batch_size,
            max_new_tokens=max_tokens,
            temperature=temperature,
        )
    elif backend in ("gemini", "nvidia"):
        decoder = GeminiChatDecoder if backend == "gemini" else NvidiaChatDecoder
        return decoder(
            name=model,
            logger=logger,
            batch_size=batch_size,
            max_new_tokens=max_tokens,
            temperature=temperature,
        )
    else:
        raise NotImplementedError
