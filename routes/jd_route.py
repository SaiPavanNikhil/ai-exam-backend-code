from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List
import io
import json
import os
import uuid

from sqlalchemy.orm import Session
from database import get_db

from models.JobDescription import JobDescription

import fitz  # PyMuPDF


router = APIRouter(
    prefix="/jd",
    tags=["Job Description"]
)


# ============================================================
# EXTRACT KEYWORDS FROM JD PDF
# ============================================================

@router.post("/extract-keywords")
async def extract_keywords(
    file: UploadFile = File(...)
):

    # --------------------------------------------------------
    # Validate file
    # --------------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected"
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )


    # --------------------------------------------------------
    # Read PDF
    # --------------------------------------------------------

    try:

        file_content = await file.read()

        pdf_document = fitz.open(
            stream=file_content,
            filetype="pdf"
        )

    except Exception as e:

        raise HTTPException(
            status_code=400,
            detail=f"Unable to read PDF: {str(e)}"
        )


    # --------------------------------------------------------
    # Extract text from all pages
    # --------------------------------------------------------

    extracted_text = ""

    try:

        for page in pdf_document:

            page_text = page.get_text()

            if page_text:
                extracted_text += page_text + "\n"

        pdf_document.close()

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Unable to extract PDF text: {str(e)}"
        )


    # --------------------------------------------------------
    # Check whether PDF contains readable text
    # --------------------------------------------------------

    if not extracted_text.strip():

        raise HTTPException(
            status_code=400,
            detail=(
                "No readable text was found in the PDF. "
                "The PDF may be scanned/image based."
            )
        )


    # --------------------------------------------------------
    # TEMPORARY KEYWORD EXTRACTION
    # --------------------------------------------------------
    #
    # We will replace this with AI-based extraction.
    #

    keywords = extract_jd_keywords(extracted_text)


    return {
        "status": "success",
        "filename": file.filename,
        "keywords": keywords
    }


# ============================================================
# BASIC JD KEYWORD EXTRACTION
# ============================================================

def extract_jd_keywords(text: str) -> List[str]:

    """
    Temporary keyword extraction.

    Later this function will use the AI model to identify
    meaningful JD-specific skills/keywords.
    """

    known_keywords = [

        # Programming
        "Python",
        "Java",
        "JavaScript",
        "TypeScript",
        "C",
        "C++",
        "C#",

        # Backend
        "FastAPI",
        "Django",
        "Flask",
        "Spring Boot",
        "REST API",
        "Microservices",

        # Frontend
        "Angular",
        "React",
        "Vue",

        # Database
        "PostgreSQL",
        "MySQL",
        "MongoDB",
        "SQL",
        "NoSQL",

        # Cloud / DevOps
        "AWS",
        "Azure",
        "GCP",
        "Docker",
        "Kubernetes",
        "Git",
        "GitHub",

        # AI / ML
        "Machine Learning",
        "Deep Learning",
        "Artificial Intelligence",
        "NLP",
        "LLM",

        # General
        "Data Structures",
        "Algorithms",
        "Object Oriented Programming",
        "System Design"
    ]


    text_lower = text.lower()

    found_keywords = []


    for keyword in known_keywords:

        if keyword.lower() in text_lower:

            found_keywords.append(keyword)


    return found_keywords

@router.post("/save")
async def save_jd(
    jd_title: str = Form(...),
    keywords: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    # ========================================================
    # VALIDATE JD TITLE
    # ========================================================

    jd_title = jd_title.strip()

    if not jd_title:
        raise HTTPException(
            status_code=400,
            detail="JD title is required"
        )


    # ========================================================
    # VALIDATE FILE
    # ========================================================

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="JD PDF is required"
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )


    # ========================================================
    # CONVERT KEYWORDS JSON STRING TO LIST
    # ========================================================

    try:

        keyword_list = json.loads(keywords)

    except json.JSONDecodeError:

        raise HTTPException(
            status_code=400,
            detail="Invalid keywords format"
        )


    if not isinstance(keyword_list, list):

        raise HTTPException(
            status_code=400,
            detail="Keywords must be a list"
        )


    # ========================================================
    # CLEAN KEYWORDS
    # ========================================================

    cleaned_keywords = []

    seen_keywords = set()

    for keyword in keyword_list:

        if not keyword:
            continue

        keyword = str(keyword).strip()

        if not keyword:
            continue

        # Prevent duplicate keywords
        normalized_keyword = keyword.lower()

        if normalized_keyword in seen_keywords:
            continue

        seen_keywords.add(normalized_keyword)

        cleaned_keywords.append(keyword)


    if not cleaned_keywords:

        raise HTTPException(
            status_code=400,
            detail="At least one keyword is required"
        )


    # ========================================================
    # CONVERT KEYWORDS TO TEXT
    # ========================================================

    keywords_text = ", ".join(cleaned_keywords)


    # ========================================================
    # READ PDF
    # ========================================================

    try:

        pdf_content = await file.read()

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Unable to read PDF: {str(e)}"
        )


    if not pdf_content:

        raise HTTPException(
            status_code=400,
            detail="Uploaded PDF is empty"
        )


    # ========================================================
    # CREATE UPLOAD DIRECTORY
    # ========================================================

    jd_upload_directory = os.path.join(
        "uploads",
        "jd"
    )

    os.makedirs(
        jd_upload_directory,
        exist_ok=True
    )


    # ========================================================
    # CREATE UNIQUE FILE NAME
    # ========================================================

    unique_filename = (
        f"{uuid.uuid4().hex}_"
        f"{file.filename}"
    )

    file_path = os.path.join(
        jd_upload_directory,
        unique_filename
    )


    # ========================================================
    # SAVE PDF
    # ========================================================

    try:

        with open(
            file_path,
            "wb"
        ) as pdf_file:

            pdf_file.write(pdf_content)

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Unable to save PDF: {str(e)}"
        )


    # ========================================================
    # SAVE JD TO DATABASE
    # ========================================================

    try:

        jd = JobDescription(

            title=jd_title,

            pdf_filename=file.filename,

            pdf_path=file_path,

            keywords=keywords_text

        )

        db.add(jd)

        db.commit()

        db.refresh(jd)


        # ====================================================
        # SUCCESS RESPONSE
        # ====================================================

        return {

            "success": True,

            "message": "JD saved successfully",

            "data": {

                "id": jd.id,

                "title": jd.title,

                "pdf_filename": jd.pdf_filename,

                "pdf_path": jd.pdf_path,

                "keywords": cleaned_keywords

            }

        }


    except Exception as e:

        # --------------------------------------------
        # Rollback DB
        # --------------------------------------------

        db.rollback()


        # --------------------------------------------
        # Remove PDF if DB save failed
        # --------------------------------------------

        if os.path.exists(file_path):

            try:

                os.remove(file_path)

            except Exception:
                pass


        print(
            f"❌ JD SAVE ERROR: {str(e)}"
        )


        raise HTTPException(
            status_code=500,
            detail=f"Unable to save JD: {str(e)}"
        )

