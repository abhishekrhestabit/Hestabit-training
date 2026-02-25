import os
import json
import yaml
import google.genai as genai

class RAGEvaluator:
    def __init__(self, config_path: str):
        cfg = yaml.safe_load(open(config_path))
        api_key = os.environ.get(cfg["api_key_env"], "")
        self._client = genai.Client(api_key=api_key)
        self._model = cfg["model_name"]

    def evaluate_response(self, user_query: str, context_used: str, generated_answer: str) -> dict:
        """Scores the answer for hallucinations and confidence."""
        prompt = f"""You are an impartial AI judge. Evaluate the generated answer.
        
        Question: {user_query}
        Factual Context Used: {context_used}
        Generated Answer: {generated_answer}

        Rules:
        1. is_faithful: True if the answer is completely supported by the Context. False if it contains hallucinations or outside information.
        2. confidence_score: A number from 0 to 100 indicating how well the answer addresses the question using ONLY the context.
        3. critique: A one-sentence explanation of your score.

        Return ONLY a raw JSON object with keys: "is_faithful", "confidence_score", "critique".
        """
        
        try:
            resp = self._client.models.generate_content(model=self._model, contents=prompt)
            # Clean up the output to ensure it's parseable JSON
            clean_json = resp.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except Exception as e:
            return {"is_faithful": True, "confidence_score": 0, "critique": f"Eval failed: {e}"}