# Add your utilities or helper functions to this file.

import os
from dotenv import load_dotenv, find_dotenv

# these expect to find a .env file at the directory above the lesson.                                                                                                                     # the format for that file is (without the comment)                                                                                                                                       #API_KEYNAME=AStringThatIsTheLongAPIKeyFromSomeService
def load_env():
    _ = load_dotenv(find_dotenv())

def get_openai_api_key():
    load_env()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    return openai_api_key


_PLACEHOLDER_OPENAI_KEYS = frozenset(
    {
        "",
        "open-ai-key",
        "your-openai-api-key",
        "your-openai-api-key-here",
        "sk-your-key-here",
        "changeme",
    }
)


def ensure_openai_api_key() -> str:
    """Load .env and fail fast with a clear message if the key is missing or a lab placeholder."""
    load_env()
    key = (os.getenv("OPENAI_API_KEY") or "").strip().strip('"').strip("'")
    if not key:
        raise ValueError(
            "OPENAI_API_KEY is not set. Export OPENAI_API_KEY='sk-...' or set it in AirAware/.env "
            "(see .env.example). To test data fetch without an LLM: python main_v1.py --dry-run"
        )
    if key.lower() in _PLACEHOLDER_OPENAI_KEYS or key.startswith("open-ai"):
        raise ValueError(
            "OPENAI_API_KEY is still the lab placeholder (e.g. open-ai-key). "
            "Replace it with a real key from https://platform.openai.com/account/api-keys "
            "or run: python main_v1.py --dry-run"
        )
    if not key.startswith("sk-"):
        raise ValueError(
            "OPENAI_API_KEY does not look valid (expected to start with sk-). "
            "Use: python main_v1.py --dry-run to skip the LLM."
        )
    return key

def get_serper_api_key():
    load_env()
    openai_api_key = os.getenv("SERPER_API_KEY")
    return openai_api_key

def get_openaq_api_key():
    load_env()
    openai_api_key = os.getenv("OPENAQ_API_KEY")
    return openai_api_key

# break line every 80 characters if line is longer than 80 characters
# don't break in the middle of a word
def pretty_print_result(result):
  parsed_result = []
  for line in result.split('\n'):
      if len(line) > 80:
          words = line.split(' ')
          new_line = ''
          for word in words:
              if len(new_line) + len(word) + 1 > 80:
                  parsed_result.append(new_line)
                  new_line = word
              else:
                  if new_line == '':
                      new_line = word
                  else:
                      new_line += ' ' + word
          parsed_result.append(new_line)
      else:
          parsed_result.append(line)
  return "\n".join(parsed_result)
