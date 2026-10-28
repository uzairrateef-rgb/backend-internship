import os

from dotenv import load_dotenv
from openai import OpenAI


# Load variables from the .env file in the project root.
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


# Read provider settings without hardcoding credentials.
base_url = os.environ["LLM_BASE_URL"]
api_key = os.environ["LLM_API_KEY"]
model = os.environ["LLM_MODEL"]


# Use the OpenAI-compatible client with OpenRouter.
# Explicit timeout and disabled automatic retries prevent hidden calls.
client = OpenAI(
    base_url=base_url,
    api_key=api_key,
    timeout=20.0,
    max_retries=0,
)


def main() -> None:
    response = client.chat.completions.create(
    model=model,
    messages=[
        {
            "role": "user",
            "content": "Reply with exactly the word: ready",
        }
    ],
    temperature=0,
    max_tokens=150,
)

    answer = response.choices[0].message.content

    if not answer:
        raise RuntimeError(
            f"Model returned no text. "
            f"Finish reason: {response.choices[0].finish_reason}"
        )

    print(answer)


if __name__ == "__main__":
    main()