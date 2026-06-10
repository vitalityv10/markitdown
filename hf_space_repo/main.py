import os
import tempfile
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from markitdown import MarkItDown

app = FastAPI(title="MarkItDown API Service")

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

md = MarkItDown()


@app.post("/convert")
async def convert_file(file: UploadFile = File(...)):
    filename = file.filename or "file.bin"
    _, ext = os.path.splitext(filename)

    # Create a temporary file with the correct extension
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_path = temp_file.name

    try:
        # Convert the file using MarkItDown
        result = md.convert(temp_path)
        return {"markdown": result.text_content}
    except Exception as e:
        return {"error": str(e)}
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.get("/health")
def health():
    return {"status": "healthy"}
