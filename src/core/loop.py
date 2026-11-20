"""Agent loop: Thought -> Code -> Observation.

The loop only coordinates three collaborators that it receives from the
outside (dependency injection): an LLM client, a code extractor and a
sandbox. It never creates them, so tests can replace them with fakes.
"""

from src.core.extraction import CodeExtractor
from src.core.prompt import PromptManager
from typing import Protocol, Any
from src.models.models_private import ExecutionResult, LLMResponse
from src.models.models_public import SolutionOutput, StepMetrics
import asyncio
import time

STOP_SEQUENCES = ["<end_code>"] #TODO ajouter d'autres stop_sequences?


class LLMClient(Protocol):
    async def generate(
            self,
            messages: list[dict[str, Any]],
            stop_sequences: list[str] | None = None,
        ) -> LLMResponse: ...


class Sandbox(Protocol):
    def execute(self, code: str) -> ExecutionResult: ...


class AgentLoop:
    def __init__(
        self,
        llm: LLMClient,
        sandbox: Sandbox,
        extractor: CodeExtractor,
        prompt_manager: PromptManager,
        max_iterations: int = 10
    ) -> None:
        self.llm: LLMClient = llm
        self.sandbox: Sandbox = sandbox
        self.extractor: CodeExtractor = extractor
        self.prompt_manager: PromptManager = prompt_manager
        self.max_iterations: int = max_iterations

    async def run(
            self, task_id: str, benchmark: str, user_prompt: str
            ) -> SolutionOutput:
        start_time = time.perf_counter()
        iterations = 1  # single turn for now; becomes the loop counter later
        system_prompt = self.prompt_manager.build_system_prompt()

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        stop_sequences = STOP_SEQUENCES

        llm_response = await self.llm.generate(messages, stop_sequences)

        extraction_result = self.extractor.extract(llm_response.text)

        # execute() is synchronous and blocks: run it in a worker thread so
        # the event loop stays free while the sandbox works.
        execution_result = await asyncio.to_thread(
            self.sandbox.execute, extraction_result.code)
        # Exécute sandbox.execute(...)
        # Ce thread est bloqué dans conn.poll(timeout) :
        # il attend que le processus worker réponde.
        # Ce qui se passe réellement pendant l'attente, dans ton projet
        # Honnêtement, aujourd'hui : rien d'autre. Avec un seul agent qui enchaîne LLM → extraction → sandbox, il n'y a aucune autre coroutine à faire avancer. Pour un seul run(), le comportement serait identique sans to_thread.
        # C'est donc une précaution peu coûteuse, utile dans trois cas à venir :

        # Un benchmark avec plusieurs tâches en parallèle : pendant qu'une sandbox travaille, les autres appels LLM continuent.
        # Une échéance globale avec asyncio.wait_for(...) : elle ne fonctionne que si la boucle n'est pas figée.
        # Un client MCP asynchrone (probable, à vérifier avec ton binôme) : les outils MCP sont appelés depuis la boucle d'événements. Si le worker doit demander au parent d'appeler un outil pendant que execute() bloque la boucle, les deux s'attendent mutuellement, ce qui est un interblocage.
        total_requests = iterations
        total_time_seconds = time.perf_counter() - start_time

        step = StepMetrics(
            step=iterations,
            input_tokens=llm_response.input_tokens,
            output_tokens=llm_response.output_tokens,
            request_time_ms=llm_response.request_time_ms,
            api_url=llm_response.api_url,
            model_name=llm_response.model_name,
            llm_output=llm_response.text,
            sandbox_input=extraction_result.code,
            sandbox_output=execution_result.output,
        )

        return SolutionOutput(
            task_id=task_id,
            benchmark=benchmark,
            success=execution_result.is_final_answer,
            solution=execution_result.final_answer_value or "",
            iterations=iterations,
            total_requests=total_requests,
            total_input_tokens=llm_response.input_tokens,
            total_output_tokens=llm_response.output_tokens,
            total_time_seconds=total_time_seconds,
            steps=[step],
            system_prompt=system_prompt,
            error=None,
        )


