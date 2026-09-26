import json
import urllib.request
import urllib.error


class AIExplainer:

    # ---------------------------------------------------------
    # LOCAL OLLAMA CONFIGURATION
    # ---------------------------------------------------------

    MODEL = "qwen2.5:1.5b"

    URL = "http://localhost:11434/api/generate"

    TIMEOUT = 180

    # Keep the context small to reduce RAM usage.
    NUM_CTX = 2048

    # Limit generated response length.
    NUM_PREDICT = 700

    # Unload the model after generation.
    KEEP_ALIVE = 0

    # ---------------------------------------------------------
    # INITIALIZE
    # ---------------------------------------------------------

    def __init__(self):

        self.model = self.MODEL
        self.url = self.URL

    # ---------------------------------------------------------
    # BUILD PROMPT
    # ---------------------------------------------------------

    def build_prompt(
        self,
        evidence: dict,
    ) -> str:

        evidence_json = json.dumps(
            evidence,
            separators=(
                ",",
                ":",
            ),
            default=str,
        )

        return f"""
You are an AML investigation assistant.

Your job is to explain suspicious activity to a financial crime investigator.

IMPORTANT RULES:

- Use ONLY the evidence provided below.
- Do not invent transactions.
- Do not invent entities.
- Do not invent relationships.
- Do not invent amounts or events.
- Do not make a final compliance or legal decision.
- Do not say that money laundering is proven.
- Explain why the entity was flagged.
- Identify the strongest evidence.
- Explain the relevant AML patterns.
- Explain the transaction and network relationships.
- Mention important limitations or missing evidence.
- Keep the explanation concise and professional.

Return the response using exactly these sections:

EXECUTIVE SUMMARY
WHY FLAGGED
KEY EVIDENCE
NETWORK ANALYSIS
TIMELINE ANALYSIS
INVESTIGATOR FOCUS
LIMITATIONS

EVIDENCE:

{evidence_json}
"""

    # ---------------------------------------------------------
    # GENERATE AI EXPLANATION
    # ---------------------------------------------------------

    def generate(
        self,
        evidence: dict,
    ) -> dict:

        prompt = self.build_prompt(
            evidence
        )

        payload = {
            "model": self.model,

            "prompt": prompt,

            "stream": False,

            "keep_alive": self.KEEP_ALIVE,

            "options": {
                "num_ctx": self.NUM_CTX,

                "num_predict": self.NUM_PREDICT,

                "temperature": 0.2,
            },
        }

        request = urllib.request.Request(
            self.url,

            data=json.dumps(
                payload
            ).encode("utf-8"),

            headers={
                "Content-Type": "application/json",
            },

            method="POST",
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=self.TIMEOUT,
            ) as response:

                raw = (
                    response
                    .read()
                    .decode("utf-8")
                )

                result = json.loads(
                    raw
                )

                explanation = (
                    result
                    .get(
                        "response",
                        "",
                    )
                    .strip()
                )

                if not explanation:

                    raise RuntimeError(
                        "Ollama returned an empty response."
                    )

                return {
                    "success": True,
                    "model": self.model,
                    "explanation": explanation,
                }

        except urllib.error.URLError as exc:

            return {
                "success": False,
                "model": self.model,
                "error": (
                    "Unable to connect to Ollama. "
                    "Make sure Ollama is running."
                ),
                "details": str(exc),
            }

        except Exception as exc:

            return {
                "success": False,
                "model": self.model,
                "error": (
                    "AI explanation generation failed."
                ),
                "details": str(exc),
            }