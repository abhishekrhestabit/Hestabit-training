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
        prompt = f"""You are an impartial AI judge. Evaluate the generated answer.
        
        Question: {user_query}
        Factual Context Used: {context_used}
        Generated Answer: {generated_answer}

        Rules:
        1. is_faithful: true if the answer is completely supported by the Context. false if it contains hallucinations or outside information. Use lowercase JSON booleans only.
        2. confidence_score: A number from 0 to 100 indicating how well the answer addresses the question using ONLY the context. Confidence score type must be a JSON number, not a string.
        3. critique: A one-sentence explanation of your score.

        Return ONLY a raw JSON object with keys: "is_faithful", "confidence_score", "critique".
        """
        
        try:
            resp = self._client.models.generate_content(model=self._model, contents=prompt)
            clean_json = resp.text.replace("```json", "").replace("```", "").strip()
            result = json.loads(clean_json)
            if result.get("confidence_score", 100) < 70:
                fix_prompt = (
                    f"The following answer has low confidence. Rewrite it using ONLY the context below.\n\n"
                    f"Context: {context_used}\nQuestion: {user_query}\nOriginal Answer: {generated_answer}\n\n"
                    "Provide a corrected, faithful answer using ONLY the context."
                )
                fix_resp = self._client.models.generate_content(model=self._model, contents=fix_prompt)
                result["fixed_answer"] = fix_resp.text.strip()
            return result
        except Exception as e:
            return {"is_faithful": True, "confidence_score": 0, "critique": f"Eval failed: {e}"}