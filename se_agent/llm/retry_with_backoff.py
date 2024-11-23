"""Utility for retrying functions with exponential backoff.

This module provides a decorator function `retry_with_exponential_backoff` that wraps a callable 
to automatically retry on specified exceptions using exponential backoff. Optionally, it supports 
jitter to introduce randomness in delay intervals.
"""

import random
import time
import openai

def retry_with_exponential_backoff(
    func,
    initial_delay: float = 1,
    exponential_base: float = 2,
    jitter: bool = True,
    max_retries: int = 10,
    errors: tuple = (openai.RateLimitError,),
):
    """Retry a function with exponential backoff.

    This function wraps a callable and retries it on specific errors with increasing delay times.
    The delay grows exponentially based on the specified base and optionally includes jitter.

    Args:
        func (Callable): The function to retry.
        initial_delay (float): The initial delay before the first retry, in seconds. Defaults to 1.
        exponential_base (float): The base for exponential backoff. Defaults to 2.
        jitter (bool): Whether to add randomness (jitter) to the delay intervals. Defaults to True.
        max_retries (int): The maximum number of retries before giving up. Defaults to 10.
        errors (tuple): A tuple of exception classes to retry on. Defaults to `(openai.RateLimitError,)`.

    Returns:
        Callable: A wrapped function that applies the retry logic.

    Raises:
        Exception: If the maximum number of retries is exceeded.
        Exception: Any exceptions not included in the `errors` tuple are raised immediately.
    """
    def wrapper(*args, **kwargs):
        # Initialize variables
        num_retries = 0
        delay = initial_delay

        # Loop until a successful response or max_retries is hit
        while True:
            try:
                return func(*args, **kwargs)

            # Retry on specified errors
            except errors as e:
                # Increment retries
                num_retries += 1

                # Check if max retries has been reached
                if num_retries > max_retries:
                    raise Exception(
                        f"Maximum number of retries ({max_retries}) exceeded."
                    )

                # Increment the delay with optional jitter
                delay *= exponential_base * (1 + jitter * random.random())

                # Sleep for the delay duration
                time.sleep(delay)

            # Raise any unexpected exceptions
            except Exception as e:
                raise e

    return wrapper