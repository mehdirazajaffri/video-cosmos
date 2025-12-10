# app/storage.py
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

# Load environment variables from .env file
load_dotenv()

STORAGE_CONN = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
BLOB_CONTAINER = os.getenv("BLOB_CONTAINER", "videos")
SAS_EXP_MIN = int(os.getenv("SAS_EXPIRY_MINUTES", "60"))

blob_service = BlobServiceClient.from_connection_string(STORAGE_CONN) if STORAGE_CONN else None

def upload_blob_from_stream(blob_name: str, stream, length: int, content_type: str):
    """
    Uploads stream to blob. stream should be file-like (bytes stream).
    """
    if blob_service is None:
        raise ValueError(
            "Azure Storage connection not configured. "
            "Please set AZURE_STORAGE_CONNECTION_STRING environment variable."
        )
    
    container_client = blob_service.get_container_client(BLOB_CONTAINER)
    # ensure container exists (idempotent-ish)
    try:
        container_client.create_container()
    except Exception:
        pass

    blob_client = container_client.get_blob_client(blob_name)
    # upload_blob accepts bytes, stream or file-like. For large files consider chunked upload.
    blob_client.upload_blob(stream, length=length, overwrite=True, content_settings=None)
    # return full blob name / url
    return blob_client.url



def generate_blob_sas_url(blob_name: str, expiry_minutes: int = SAS_EXP_MIN):
    """
    Create a SAS URL for a blob (signed with account key). For production prefer user-delegation SAS.
    """
    if not ACCOUNT_NAME or not ACCOUNT_KEY:
        raise ValueError(
            "Azure Storage account credentials not configured. "
            "Please set AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY environment variables."
        )
    
    expiry = datetime.utcnow() + timedelta(minutes=expiry_minutes)
    sas_token = generate_blob_sas(
        account_name=ACCOUNT_NAME,
        container_name=BLOB_CONTAINER,
        blob_name=blob_name,
        account_key=ACCOUNT_KEY,
        permission=BlobSasPermissions(read=True),
        expiry=expiry
    )
    blob_url = f"https://{ACCOUNT_NAME}.blob.core.windows.net/{BLOB_CONTAINER}/{blob_name}?{sas_token}"
    return blob_url