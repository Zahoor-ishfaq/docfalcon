"""Pydantic models for LLM extraction output."""

from typing import Optional
from pydantic import BaseModel


class IqamaExtraction(BaseModel):
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    iqama_number: Optional[str] = None
    nationality: Optional[str] = None
    profession: Optional[str] = None
    expiry_date: Optional[str] = None
    employer: Optional[str] = None


class VisaExtraction(BaseModel):
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    passport_number: Optional[str] = None
    visa_number: Optional[str] = None
    visa_type: Optional[str] = None
    expiry_date: Optional[str] = None
    sponsor: Optional[str] = None


class ContractExtraction(BaseModel):
    employee_name: Optional[str] = None
    employer: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    salary: Optional[str] = None


EXTRACTION_MODELS = {
    "iqama": IqamaExtraction,
    "visa": VisaExtraction,
    "contract": ContractExtraction,
}