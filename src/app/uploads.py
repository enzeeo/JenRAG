from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re


MARKDOWN_UPLOAD_DIRECTORY = "data/md"
LATEX_UPLOAD_DIRECTORY = "data/latex"
PDF_UPLOAD_DIRECTORY = "data/pdf"
MAX_MARKDOWN_UPLOAD_SIZE_BYTES = 2 * 1024 * 1024
MAX_LATEX_UPLOAD_SIZE_BYTES = 2 * 1024 * 1024
MAX_PDF_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024
MIN_YEAR = 2000
MAX_YEAR = 2100
VALID_QUARTERS = {"fall", "win", "spring"}
PRESET_WORK_TYPES = {
    "pset",
    "hw",
    "midterm",
    "final",
    "exam",
    "quiz",
    "notes",
    "lec",
    "custom",
}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PROFESSOR_LAST_NAME_PATTERN = re.compile(r"^[a-z]+(?:-[a-z]+)*$")
COURSE_CATEGORY_PATTERN = re.compile(r"^[A-Za-z]+$")
COURSE_NUMBER_PATTERN = re.compile(r"^\d{5}$")
WORK_NUMBER_PATTERN = re.compile(r"^\d+$")


class UploadValidationError(ValueError):
    """Raised when upload metadata or file content fails validation."""


@dataclass(frozen=True)
class UploadMetadata:
    course_category: str
    course_number: str
    quarter: str
    year: int
    work_segment: str
    professor_last_name: str
    submitter_email: str
    submission_note: str


@dataclass(frozen=True)
class ValidatedUploadedFile:
    file_name: str
    extension: str
    file_bytes: bytes


def normalize_upload_metadata(
    course_category: str,
    course_number: str,
    quarter: str,
    year: str | int,
    work_type: str,
    work_number: str,
    custom_work_type: str,
    professor_last_name: str,
    submitter_email: str,
    submission_note: str,
) -> UploadMetadata:
    """Validate and normalize all metadata fields for a new upload."""
    normalized_course_category = normalize_course_category(course_category)
    normalized_course_number = normalize_course_number(course_number)
    normalized_quarter = normalize_quarter(quarter)
    normalized_year = normalize_year(year)
    normalized_work_segment = normalize_work_segment(
        work_type=work_type,
        work_number=work_number,
        custom_work_type=custom_work_type,
    )
    normalized_professor_last_name = normalize_professor_last_name(professor_last_name)
    normalized_submitter_email = normalize_submitter_email(submitter_email)
    normalized_submission_note = submission_note.strip()

    return UploadMetadata(
        course_category=normalized_course_category,
        course_number=normalized_course_number,
        quarter=normalized_quarter,
        year=normalized_year,
        work_segment=normalized_work_segment,
        professor_last_name=normalized_professor_last_name,
        submitter_email=normalized_submitter_email,
        submission_note=normalized_submission_note,
    )


def normalize_course_category(course_category: str) -> str:
    """Return lowercase course category like 'cmsc'."""
    stripped_course_category = course_category.strip()
    if not stripped_course_category:
        raise UploadValidationError("Course category is required.")
    if not COURSE_CATEGORY_PATTERN.fullmatch(stripped_course_category):
        raise UploadValidationError("Course category must contain letters only.")
    return stripped_course_category.lower()


def normalize_course_number(course_number: str) -> str:
    """Return a validated five-digit course number."""
    stripped_course_number = course_number.strip()
    if not COURSE_NUMBER_PATTERN.fullmatch(stripped_course_number):
        raise UploadValidationError("Course number must be exactly five digits.")
    return stripped_course_number


def normalize_quarter(quarter: str) -> str:
    """Return a validated academic quarter token."""
    normalized_quarter = quarter.strip().lower()
    if normalized_quarter not in VALID_QUARTERS:
        raise UploadValidationError("Quarter must be one of: fall, win, spring.")
    return normalized_quarter


def normalize_year(year: str | int) -> int:
    """Return a validated year in the supported range."""
    try:
        normalized_year = int(str(year).strip())
    except ValueError as error:
        raise UploadValidationError("Year must be a four-digit number.") from error

    if normalized_year < MIN_YEAR or normalized_year > MAX_YEAR:
        raise UploadValidationError(
            f"Year must be between {MIN_YEAR} and {MAX_YEAR}."
        )
    return normalized_year


def normalize_work_segment(
    work_type: str,
    work_number: str,
    custom_work_type: str,
) -> str:
    """Build a normalized work segment like 'pset1' or 'midterm'."""
    normalized_work_type = work_type.strip().lower()
    if normalized_work_type not in PRESET_WORK_TYPES:
        raise UploadValidationError("Work type is not supported.")

    if normalized_work_type == "custom":
        normalized_custom_work_type = slugify_alphanumeric(custom_work_type)
        if not normalized_custom_work_type:
            raise UploadValidationError("Custom work type is required.")
        return normalized_custom_work_type

    stripped_work_number = work_number.strip()
    if stripped_work_number and not WORK_NUMBER_PATTERN.fullmatch(stripped_work_number):
        raise UploadValidationError("Work number must contain digits only.")

    if stripped_work_number:
        return f"{normalized_work_type}{stripped_work_number}"

    return normalized_work_type


def normalize_professor_last_name(professor_last_name: str) -> str:
    """Return a lowercase professor last name token safe for filenames."""
    normalized_professor_last_name = professor_last_name.strip().lower()
    if not normalized_professor_last_name:
        raise UploadValidationError("Professor last name is required.")
    if not PROFESSOR_LAST_NAME_PATTERN.fullmatch(normalized_professor_last_name):
        raise UploadValidationError(
            "Professor last name must use letters and single hyphens only."
        )
    return normalized_professor_last_name


def normalize_submitter_email(submitter_email: str) -> str:
    """Return a normalized submitter email address."""
    normalized_submitter_email = submitter_email.strip().lower()
    if not normalized_submitter_email:
        raise UploadValidationError("Submitter email is required.")
    if not EMAIL_PATTERN.fullmatch(normalized_submitter_email):
        raise UploadValidationError("Submitter email is not valid.")
    return normalized_submitter_email


def build_course_folder(upload_metadata: UploadMetadata) -> str:
    """Return folder name like 'cmsc_27100'."""
    return f"{upload_metadata.course_category}_{upload_metadata.course_number}"


def build_filename_stem(upload_metadata: UploadMetadata) -> str:
    """Return filename stem without extension."""
    course_folder = build_course_folder(upload_metadata)
    return (
        f"{course_folder}_{upload_metadata.quarter}_{upload_metadata.year}_"
        f"{upload_metadata.work_segment}_{upload_metadata.professor_last_name}"
    )


def build_target_path(upload_metadata: UploadMetadata, extension: str) -> str:
    """Return repo path for a validated upload."""
    normalized_extension = extension.strip().lower()
    filename_stem = build_filename_stem(upload_metadata)
    course_folder = build_course_folder(upload_metadata)

    if normalized_extension == ".tex":
        return f"{LATEX_UPLOAD_DIRECTORY}/{course_folder}/{filename_stem}.tex"
    if normalized_extension == ".pdf":
        return f"{PDF_UPLOAD_DIRECTORY}/{course_folder}/{filename_stem}.pdf"
    if normalized_extension == ".md":
        return f"{MARKDOWN_UPLOAD_DIRECTORY}/{course_folder}/{filename_stem}.md"

    raise UploadValidationError("Only .md, .tex, and .pdf uploads are supported.")


def validate_uploaded_file(file_name: str, file_bytes: bytes) -> ValidatedUploadedFile:
    """Validate file extension, size, and basic content shape."""
    if not file_name:
        raise UploadValidationError("Upload file is required.")

    normalized_file_name = file_name.strip()
    normalized_extension = ""
    if "." in normalized_file_name:
        normalized_extension = "." + normalized_file_name.rsplit(".", 1)[1].lower()

    if normalized_extension == ".md":
        validate_markdown_file(file_bytes)
    elif normalized_extension == ".tex":
        validate_latex_file(file_bytes)
    elif normalized_extension == ".pdf":
        validate_pdf_file(file_bytes)
    else:
        raise UploadValidationError("Only .md, .tex, and .pdf uploads are supported.")

    return ValidatedUploadedFile(
        file_name=normalized_file_name,
        extension=normalized_extension,
        file_bytes=file_bytes,
    )


def validate_latex_file(file_bytes: bytes) -> None:
    """Validate file size and ensure LaTeX bytes decode as UTF-8 text."""
    if len(file_bytes) == 0:
        raise UploadValidationError("LaTeX file is empty.")
    if len(file_bytes) > MAX_LATEX_UPLOAD_SIZE_BYTES:
        raise UploadValidationError("LaTeX file exceeds the 2 MB size limit.")

    try:
        latex_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise UploadValidationError("LaTeX file must be valid UTF-8 text.") from error

    if not latex_text.strip():
        raise UploadValidationError("LaTeX file is empty.")


def validate_markdown_file(file_bytes: bytes) -> None:
    """Validate file size and ensure Markdown bytes decode as UTF-8 text."""
    if len(file_bytes) == 0:
        raise UploadValidationError("Markdown file is empty.")
    if len(file_bytes) > MAX_MARKDOWN_UPLOAD_SIZE_BYTES:
        raise UploadValidationError("Markdown file exceeds the 2 MB size limit.")

    try:
        markdown_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise UploadValidationError("Markdown file must be valid UTF-8 text.") from error

    if not markdown_text.strip():
        raise UploadValidationError("Markdown file is empty.")


def validate_pdf_file(file_bytes: bytes) -> None:
    """Validate file size and ensure PDF bytes start with a PDF header."""
    if len(file_bytes) == 0:
        raise UploadValidationError("PDF file is empty.")
    if len(file_bytes) > MAX_PDF_UPLOAD_SIZE_BYTES:
        raise UploadValidationError("PDF file exceeds the 20 MB size limit.")
    if not file_bytes.startswith(b"%PDF-"):
        raise UploadValidationError("PDF file does not have a valid PDF header.")


def slugify_alphanumeric(value: str) -> str:
    """Lowercase text and keep letters plus digits only."""
    lowercase_value = value.strip().lower()
    return "".join(character for character in lowercase_value if character.isalnum())


def build_upload_branch_name(
    upload_metadata: UploadMetadata,
    timestamp: datetime | None = None,
) -> str:
    """Return branch name like upload/cmsc_27100/file-20260430T231522Z."""
    timestamp_value = timestamp or datetime.now(timezone.utc)
    timestamp_fragment = timestamp_value.strftime("%Y%m%dT%H%M%SZ")
    course_folder = build_course_folder(upload_metadata)
    filename_stem = build_filename_stem(upload_metadata)
    return f"upload/{course_folder}/{filename_stem}-{timestamp_fragment}"
