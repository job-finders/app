from typing import Optional, List, Type
from pydantic import BaseModel, Field

from src.database.models.company_models import Company, CompanyCIPC
from src.agents.base import BaseAgent

class DocumentVerificationInput(BaseModel):
    __doc__ = """
    Input schema for evaluating the authenticity of a submitted company-related document using AI agents.

    This model provides a comprehensive data package used to verify various types of documents submitted
    by companies or their directors. It includes the event_type of document, the document contents (PDF), and
    contextual metadata such as director identity and registered company information. AI agents can use
    this structured input to:

    - Detect if the document appears genuine, suspicious, tampered with, or incomplete.
    - Compare submitted document text with expected values (e.g., director name and ID number).
    - Cross-check company registration numbers and data with CIPC records.
    - Evaluate alignment between the ID card and any other director-linked documents.
    - Validate consistency between internal records (on JobFinders) and external registrations.
    - Identify red flags or anomalies, and escalate the document for human review if necessary.

    This input format supports a wide range of South African business verification scenarios,
    including CIPC documents, B-BBEE certificates, municipal statements, VAT certificates,
    and more.
    """
    document_type: str = Field(..., description="Type of document being reviewed, e.g. 'id_card', 'company_registration', 'proof_of_address', etc.")
    supplied_document_pdf: str = Field(..., description="PDF document to be tested together with the supplied data for authenticity")
    director_name: Optional[str] = Field(None, description="Name of the director to match in the document")
    id_number: Optional[str] = Field(None, description="ID number of the director for validation")
    director_id_card_pdf: Optional[str] = Field(None, description="Text extracted from the submitted ID card for comparison")
    cipc_company_data: Optional[CompanyCIPC] = Field(None, description="Company CIPC Registration Record Supplied as a PDF Document")
    company_data: Optional[Company] = Field(None, description="Company Official Record on Jobfinders - Also Perform Sanity Checks on this record to determine if Company Record is not Fake")

class DocumentVerificationOutPut(BaseModel):
    __doc__ = """
    Output Fields for Document Verifications for all types of Company Documents
    This model captures both automated results and flags for manual intervention.
    Each field represents specific checks and insights from the AI agent.
    """

    is_document_valid: bool = Field(..., description="Whether the document is deemed authentic and valid.")
    reason: Optional[str] = Field(None, description="If invalid or uncertain, provides the reasoning or detected anomaly.")

    match_director_name: Optional[bool] = Field(
        None, description="Whether the director's name in the document matches the expected name from records."
    )
    match_id_number: Optional[bool] = Field(
        None, description="Whether the ID number in the document matches the director's known ID number."
    )
    match_cipc_data: Optional[bool] = Field(
        None, description="Whether the document details align with CIPC records, such as registration number, company name, etc."
    )
    match_company_profile_data: Optional[bool] = Field(
        None, description="Whether the document details are consistent with the JobFinders company profile data."
    )

    cipc_number_verified_online: Optional[bool] = Field(
        None, description="Whether the CIPC registration number was found valid using an external verification service."
    )
    cipc_number_verification_notes: Optional[str] = Field(
        None, description="Additional details about the verification attempt of the CIPC number, e.g., if no record was found."
    )

    is_suspicious: Optional[bool] = Field(
        False, description="Whether the document has traits that look fraudulent, tampered with, or AI-generated."
    )
    suspicious_notes: Optional[str] = Field(
        None, description="Explanation or evidence suggesting the document may be suspicious."
    )

    requires_human_review: Optional[bool] = Field(
        default=False, description="Whether this document needs to be manually reviewed by a human based on AI uncertainty or fraud likelihood."
    )
    document_type: str = Field(..., description="Echo back the document event_type being validated.")

    score: Optional[float] = Field(
        None, description="A confidence score from 0.0 to 1.0 indicating AI's certainty about the document's validity."
    )
    reviewer_notes: Optional[str] = Field(
        None, description="Structured summary for a human reviewer outlining what was checked and any key mismatches or issues."
    )

class DocumentVerificationAgent(BaseAgent):
    name = "DocumentVerificationAgent"
    description = "Validates company documents by checking format, identity match, and consistency with official records."

    def system_prompt(self) -> str:
        """Returns System Prompt"""
        return (
            "You are a professional South African document verification assistant. "
            "Your task is to assess the validity and authenticity of company documents. "
            "Cross-check director name and ID with the supplied ID card. "
            "Compare the contents of the document with CIPC and company registration data. "
            "Look for signs of forgery or inconsistent formatting. Flag suspicious items. "
            "Your output must strictly follow the structure of the DocumentVerificationOutPut Pydantic model."
        )

    def prompt(self, input: DocumentVerificationInput) -> str:
        return (
            f"You are reviewing a company document for authenticity.\n"
            f"Document Type: {input.document_type}\n"
            f"---\n"
            f"Supplied Document (PDF/Text):\n{input.supplied_document_pdf}\n"
            f"---\n"
            f"Director Name (Expected): {input.director_name or 'N/A'}\n"
            f"Director ID Number (Expected): {input.id_number or 'N/A'}\n"
            f"---\n"
            f"Reference Director ID Card (Text):\n{input.director_id_card_pdf or 'N/A'}\n"
            f"---\n"
            f"CIPC Registration Data:\n{input.cipc_company_data.model_dump_json() if input.cipc_company_data else 'N/A'}\n"
            f"---\n"
            f"Company Profile on Platform:\n{input.company_data.model_dump_json() if input.company_data else 'N/A'}\n"
            f"---\n"
            f"Instructions:\n"
            f"1. Compare names and ID numbers for consistency.\n"
            f"2. Validate that document text matches the CIPC or company records where applicable.\n"
            f"3. Look for suspicious formatting or obvious forgery patterns.\n"
            f"4. If confidence is low or information is inconsistent, suggest human review.\n"
            f"Return a structured response using only the DocumentVerificationOutPut fields."
        )

    def output_model(self) -> Type[BaseModel]:
        return DocumentVerificationOutPut
