from dataclasses import dataclass
from typing import Any

from src.llm.client import LLMClient
from src.rag.chunker import CodeChunk
from src.rag.prompt_templates import PromptTemplateManager


@dataclass(frozen=True)
class ProcessedChunk:
    chunk: CodeChunk
    summary: str
    document: str


class EmbeddingGenerator:
    def __init__(self, embedding_function: Any, summarization_client: LLMClient, prompt_manager: PromptTemplateManager):
        self.embedding_function = embedding_function
        self.summarization_client = summarization_client
        self.prompt_manager = prompt_manager
    
    async def generate(self, chunk: CodeChunk) -> ProcessedChunk:
        prompt = self.prompt_manager.get(
            "code_summarization",
            symbol_type=chunk.symbol_type,
            code_content=chunk.content
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        response = await self.summarization_client.get_response(messages=messages)
        
        if response and response.choices:
            summary = response.choices[0].message.content.strip()
        else:
            summary = f"A {chunk.symbol_type} named {chunk.symbol_name}"
        
        document = f"{summary}\n\n{chunk.content}"
        
        return ProcessedChunk(
            chunk=chunk,
            summary=summary,
            document=document
        )
