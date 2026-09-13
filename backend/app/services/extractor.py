import json
from typing import Dict, Any, List, Optional
from app.services.llm import llm_service

class DocumentExtractorService:
    async def extract_structured_data(
        self,
        markdown_content: str,
        schema_name: str,
        target_fields: Optional[List[str]] = None,
        custom_instructions: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extracts structured JSON entity data from the document text
        based on the requested schema and fields.
        """
        fields_str = ", ".join(target_fields) if target_fields else "All primary entities, keys, dates, tables, amounts, and identifiers."

        system_prompt = (
            "You are a state-of-the-art Document Information Extraction Engine. "
            "Your objective is to extract key-value data, nested line items, and metadata from the document into valid JSON format. "
            "You must output ONLY valid JSON without markdown fences (or enclosed in a single ```json block)."
        )

        user_prompt = f"""Document Content:
{markdown_content[:15000]}

Extraction Schema: {schema_name}
Target Fields: {fields_str}
Custom Instructions: {custom_instructions or 'Extract clean normalized key-value fields and table line items.'}

Return a valid JSON object representing the extracted fields:"""

        response = await llm_service.generate_response(
            system_prompt, 
            user_prompt, 
            temperature=0.0, 
            json_format=True,
            provider=provider,
            model=model
        )
        raw_text = response.get("text", "{}")

        # Parse JSON from LLM output
        try:
            # Strip backticks if present
            cleaned = raw_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
            return {
                "status": "success",
                "extracted_data": data,
                "model_used": response.get("model")
            }
        except Exception as e:
            return {
                "status": "partial_success",
                "extracted_data": {"raw_output": raw_text, "parse_error": str(e)},
                "model_used": response.get("model")
            }

extractor_service = DocumentExtractorService()
