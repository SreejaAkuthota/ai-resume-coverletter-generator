# utils.py
import os, json
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class StyleConfig(BaseModel):
    tone: str = Field(default="professional, confident")
    seniority: str = Field(default="mid-senior")
    layout: str = Field(default="modern ATS-friendly")

class LLMClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        # prefer explicit env; fallbacks handled below
        self.openai_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.groq_key   = os.getenv("GROQ_API_KEY", "")
        self.openai_model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.groq_model   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

        self.backend = None
        if self.openai_key:
            from openai import OpenAI
            self.backend = "openai"
            self.client = OpenAI(api_key=self.openai_key)
        elif self.groq_key:
            from groq import Groq
            self.backend = "groq"
            self.client = Groq(api_key=self.groq_key)
        else:
            raise RuntimeError(
                "No API key found. Set OPENAI_API_KEY or GROQ_API_KEY in Secrets/Env."
            )

    def complete_json(self, prompt: str) -> dict:
        if self.backend == "openai":
            resp = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "Return strictly valid JSON unless told otherwise."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
            )
            text = resp.choices[0].message.content
        else:  # groq
            resp = self.client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {"role": "system", "content": "Return strictly valid JSON unless told otherwise."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
            )
            text = resp.choices[0].message.content

        try:
            start = text.find("{"); end = text.rfind("}")
            return json.loads(text[start:end+1])
        except Exception:
            raise ValueError(f"Model did not return valid JSON. Raw: {text[:500]}")

    def complete_markdown(self, prompt: str, temperature: float = 0.6) -> str:
        if self.backend == "openai":
            resp = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "Return clean Markdown."},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
            )
            return resp.choices[0].message.content
        else:
            resp = self.client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {"role": "system", "content": "Return clean Markdown."},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
            )
            return resp.choices[0].message.content

def safe_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in "._- ").strip().replace(" ", "_") or "output"
