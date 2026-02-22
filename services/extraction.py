"""Groq LLM structured extraction service."""

import json
import logging
import re
from openai import OpenAI

from config import settings
from schemas.extraction import JobExtraction, MaterialUsed

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI assistant for FieldOps AI, a field service management system.
Your job is to extract structured data from voice transcripts of field service workers.

Extract the following information accurately:
- customer_name: The customer or client name mentioned
- job_type: Type of work performed (plumbing, electrical, HVAC, painting, carpentry, general maintenance, etc.)
- labor_hours: Hours worked (numeric)
- follow_up_date: If a follow-up is mentioned, extract the date (convert relative dates like "6 months" to an ISO date) or null
- follow_up_reason: Why follow-up is needed or null
- invoice_required: True if the job was completed and should be billed (default true). Set to false if the user explicitly says not to bill.
- confidence_score: Confidence in extraction accuracy (0.0 to 1.0)

For materials used, return a list where each item has:
- item: Material name
- quantity: Quantity used (integer)
- unit: Unit of measurement (default to "piece" if not mentioned)

Rules:
- Parse relative dates: "6 months" = 6 months from today, "next week" = 7 days from today
- Always attempt to infer job_type from context even if not explicitly stated
- If someone says "don't bill" or "no charge", set invoice_required to false
- Respond ONLY with valid JSON matching the exact schema provided. Do not include markdown formatting or extra text.
"""

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "customer_name": {"type": "string"},
        "job_type": {"type": "string"},
        "materials_used": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "unit": {"type": "string"}
                },
                "required": ["item", "quantity", "unit"]
            }
        },
        "labor_hours": {"type": "number"},
        "follow_up_date": {"type": ["string", "null"]},
        "follow_up_reason": {"type": ["string", "null"]},
        "invoice_required": {"type": "boolean"},
        "confidence_score": {"type": "number"}
    },
    "required": ["customer_name", "job_type", "labor_hours", "invoice_required", "confidence_score", "materials_used"]
}


async def extract_job_data(transcript: str) -> JobExtraction:
    """
    Extract structured job data from a transcript using Groq LLM API.
    """
    logger.info(f"Extracting structured data from transcript: {transcript[:80]}...")

    try:
        client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.GROQ_API_KEY,
        )

        response = client.chat.completions.create(
            model=settings.GROQ_LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract job data from this transcript and return ONLY JSON:\n\n\"{transcript}\""}
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=500,
        )

        content = response.choices[0].message.content
        
        # Strip any potential markdown wrappers
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        
        extracted_data = json.loads(content)
        logger.info(f"Raw extraction: {json.dumps(extracted_data, indent=2)}")

        # Normalize materials
        materials = []
        for mat in extracted_data.get("materials_used", []):
            materials.append(MaterialUsed(
                item=mat.get("item", "Unknown"),
                quantity=mat.get("quantity", 1),
                unit=mat.get("unit", "piece"),
            ))

        # Build validated extraction
        extraction = JobExtraction(
            customer_name=extracted_data.get("customer_name", "Unknown"),
            job_type=extracted_data.get("job_type", "Unknown"),
            materials_used=materials,
            labor_hours=extracted_data.get("labor_hours", 1.0),
            follow_up_date=extracted_data.get("follow_up_date"),
            follow_up_reason=extracted_data.get("follow_up_reason"),
            invoice_required=extracted_data.get("invoice_required", True),
            confidence_score=extracted_data.get("confidence_score", 0.85),
            raw_transcript=transcript,
        )

        logger.info(f"Validated extraction: {extraction.customer_name} - {extraction.job_type}")
        return extraction

    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}")
        raise
