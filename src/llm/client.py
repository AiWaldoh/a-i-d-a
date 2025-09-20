import time
from typing import Dict, Any, Optional

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from src.config.settings import AppSettings
from src.llm.types import LLMConfig


class LLMClient:
    def __init__(self, config: Optional[LLMConfig] = None, logger=None):
        self.config = config or AppSettings.LLM_CONFIG
        self.logger = logger
        self._client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries,
        )

    async def get_response(
        self,
        messages: list,
        tools: list = None
    ) -> Optional[ChatCompletion]:
        """
        Gets a full response object from the LLM, including all metadata.

        Args:
            messages: A list of messages forming the conversation history.
            tools: An optional list of tools to provide to the LLM.

        Returns:
            The raw ChatCompletion object from the OpenAI API, or None on failure.
        """
        params = {
            "model": self.config.model,
            "messages": messages,
        }
        
        # Add model-specific parameters if they exist in the config
        if self.config.temperature is not None:
            params["temperature"] = self.config.temperature
        if self.config.top_p is not None:
            params["top_p"] = self.config.top_p
        if self.config.max_tokens is not None:
            params["max_tokens"] = self.config.max_tokens
            
        # These are custom params for openrouter, not standard in openai
        if self.config.reasoning_effort:
            params["reasoning_effort"] = self.config.reasoning_effort
        if self.config.verbosity:
            params["verbosity"] = self.config.verbosity
            
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"
        else:
            # Ensure JSON object response when not using tools
            params["response_format"] = {"type": "json_object"}

        start_time = time.time()
        try:
            response = await self._client.chat.completions.create(**params)

            if self.config.response_parser == "qwen_thinking":
                # The response content is a string that contains <think>...</think> followed by JSON
                raw_content = response.choices[0].message.content
                # Find the end of the thinking tag
                think_end_tag = "</think>"
                json_start_index = raw_content.rfind(think_end_tag)
                
                if json_start_index != -1:
                    # Extract the JSON part after the tag
                    json_string = raw_content[json_start_index + len(think_end_tag):].strip()
                    # We need to modify the response object itself, which is immutable.
                    # So, we create a new message object and choice object.
                    
                    from openai.types.chat import ChatCompletionMessage, ChatCompletion
                    from openai.types.chat.chat_completion import Choice
                    
                    new_message = ChatCompletionMessage(
                        role=response.choices[0].message.role,
                        content=json_string
                    )
                    
                    new_choice = Choice(
                        finish_reason=response.choices[0].finish_reason,
                        index=response.choices[0].index,
                        message=new_message
                    )
                    
                    # Reconstruct the response object
                    response = ChatCompletion(
                        id=response.id,
                        choices=[new_choice],
                        created=response.created,
                        model=response.model,
                        object=response.object,
                        system_fingerprint=response.system_fingerprint,
                        usage=response.usage
                    )

            duration = time.time() - start_time

            if self.logger:
                self.logger.log_api_call(duration, response.model, response.usage)

            return response
        except Exception as e:
            if self.logger:
                self.logger.log_error("Error getting LLM response", e)
            return None
