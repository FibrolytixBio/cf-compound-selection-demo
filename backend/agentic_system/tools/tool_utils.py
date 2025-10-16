import fcntl
import json
import time
import asyncio
from pathlib import Path
import diskcache
from functools import wraps
import inspect

import dspy
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

# ============================= AI Tool Summarizer ==============================

summarizer_lm = dspy.LM(
    "gemini/gemini-2.5-flash-lite", temperature=0.0, cache=True, max_tokens=50000
)


# DSPy signature for summarizing data
class SummarizeData(dspy.Signature):
    """Summarize raw API data into useful tokens for an agent.
    For each distinct piece of information, provide a concise statement followed by a parenthetical citation to the specific source (full URL, PMID, assay ID, etc.) from the API data.
    Do not combine information from multiple sources in a single statement.
    Only include information directly supported by the data.
    Do not add external knowledge or inferences.
    If there is no useful information, return "No relevant information found."
    """

    goal: str = dspy.InputField(
        desc="The desired information to obtain with this tool call"
    )
    data: str = dspy.InputField(desc="The raw data from the tool call")
    summary: str = dspy.OutputField(
        desc="A concise, structured summary of key information formatted for use by ReAct agent LLM"
    )


def ai_summarized_output(func):
    """Decorator that calls the original function and summarizes its output using Gemini Flash Lite, adding a 'goal' parameter."""

    # Check if already decorated
    if hasattr(func, "goal_info"):
        return func

    goal_desc = "Concisely state the specific desired information to obtain with this tool call."

    # Update docstring
    new_doc = func.__doc__
    if new_doc:
        lines = new_doc.split("\n")
        new_lines = []
        in_args = False
        for line in lines:
            new_lines.append(line)
            if line.strip().startswith("Args:"):
                in_args = True
                new_lines.append(f"        goal (str): {goal_desc}")
            elif in_args and line.strip() == "":
                in_args = False
        new_doc = "\n".join(new_lines)
    else:
        new_doc = f"Args:\n        goal (str): {goal_desc}"

    # Update signature
    sig = inspect.signature(func)
    goal_param = inspect.Parameter(
        "goal", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str
    )
    new_params = [goal_param] + list(sig.parameters.values())
    new_sig = sig.replace(parameters=new_params)

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Bind arguments to the new signature
        bound = new_sig.bind(*args, **kwargs)
        bound.apply_defaults()
        goal = bound.arguments["goal"]  # goal parameter for future use in summarization

        # Prepare arguments for the original function
        original_kwargs = bound.arguments.copy()
        del original_kwargs["goal"]

        result = str(func(**original_kwargs))

        # Use DSPy to summarize
        with dspy.context(lm=summarizer_lm):
            predict = dspy.Predict(SummarizeData)
            summary_result = predict(goal=goal, data=result)
            return summary_result.summary

    wrapper.__signature__ = new_sig
    wrapper.__doc__ = new_doc
    wrapper.goal_info = goal_desc
    return wrapper


# ============================ Caching and Rate Limiting =============================


def tool_cache(name: str, enabled: bool = True):
    """
    Decorator to cache function results using diskcache.
    Creates a cache directory at /tmp/{name}_cache.

    Args:
        name (str): Name for the cache (e.g., "chembl", "pubchem")
        enabled (bool): Whether to enable caching. Defaults to False.

    Returns:
        Decorated function with caching enabled if enabled=True, otherwise the original function

    Usage:
        @tool_cache("chembl", enabled=True)
        def my_function(arg1, arg2):
            return expensive_operation(arg1, arg2)
    """

    def decorator(func):
        if not enabled:
            return func

        cache = diskcache.Cache(f"/tmp/{name}_cache")

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a hashable key from function name and arguments
            key = (func.__name__, args, tuple(sorted(kwargs.items())))

            # Check cache first
            if key in cache:
                return cache[key]

            # Call function and cache result with 3-day expiration
            result = func(*args, **kwargs)
            expire_time = time.time() + (3 * 24 * 60 * 60)  # 3 days in seconds
            cache.set(key, result, expire=expire_time)
            return result

        return wrapper

    return decorator


class FileBasedRateLimiter:
    def __init__(
        self, max_requests: int = 3, time_window: float = 1.0, name: str = "default"
    ):
        self.max_requests = max_requests
        self.time_window = time_window
        self.state_file = Path(f"/tmp/{name}_rate_limiter.json")

    async def acquire(self):
        """Async version for async use"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._acquire_sync)

    def acquire_sync(self):
        """Synchronous version for non-async use"""
        self._acquire_sync()

    def _acquire_sync(self):
        # Create file if it doesn't exist
        if not self.state_file.exists():
            self.state_file.write_text(json.dumps({"requests": []}))

        # Acquire exclusive lock
        with open(self.state_file, "r+") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                data = json.load(f)
                current_time = time.time()

                # Clean old requests
                data["requests"] = [
                    req
                    for req in data["requests"]
                    if current_time - req < self.time_window
                ]

                # Check if we need to wait
                if len(data["requests"]) >= self.max_requests:
                    oldest = data["requests"][0]
                    wait_time = self.time_window - (current_time - oldest)
                    if wait_time > 0:
                        time.sleep(wait_time)
                        current_time = time.time()
                        data["requests"] = [
                            req
                            for req in data["requests"]
                            if current_time - req < self.time_window
                        ]

                # Add current request
                data["requests"].append(current_time)

                # Write back
                f.seek(0)
                json.dump(data, f)
                f.truncate()
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
