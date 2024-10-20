import reflex as rx
import tempfile
from embedchain import App
import os

message_style = dict(display="inline-block", padding="2em", border_radius="8px",
                     max_width=["120em", "120em", "80em", "80em", "80em", "80em"])

class State(rx.State):
    """The app state."""
    messages: list[dict] = []
    db_path: str = tempfile.mkdtemp()
    knowledge_base_files: list[str] = []
    user_question: str = ""
    upload_status: str = ""

    # To store uploaded files temporarily
    uploaded_files: list[rx.UploadFile] = []

    def get_app(self):
        return App.from_config(
            config={
                "llm": {"provider": "ollama",
                        "config": {"model": "llama3.2:latest", "max_tokens": 250, "temperature": 0.5, "stream": True,
                                   "base_url": 'http://localhost:11434'}},
                "vectordb": {"provider": "chroma", "config": {"dir": self.db_path}},
                "embedder": {"provider": "ollama",
                             "config": {"model": "llama3.2:latest", "base_url": 'http://localhost:11434'}},
            }
        )

    async def upload_and_process_files(self, files: list[rx.UploadFile]):
        """Handle file upload and processing in one step."""
        if not files:
            self.upload_status = "No file uploaded!"
            return

        self.uploaded_files = files  # Store the uploaded files
        self.upload_status = f"Uploading and processing {len(files)} file(s)."

        for file in self.uploaded_files:
            upload_data = await file.read()
            outfile = rx.get_upload_dir() / file.filename
            
            # Save the file
            with outfile.open("wb") as file_object:
                file_object.write(upload_data)

            # Process and add to knowledge base
            app = self.get_app()
            app.add(str(outfile), data_type="pdf_file")
            self.knowledge_base_files.append(file.filename)

        self.upload_status = f"Uploaded and processed {len(self.uploaded_files)} file(s) successfully!"
        self.uploaded_files = []  # Clear uploaded files after processing

    async def process_existing_files(self):
        """Process all existing PDF files in the upload directory on startup."""
        upload_dir = rx.get_upload_dir()
        existing_files = [file for file in os.listdir(upload_dir) if file.endswith('.pdf')]
        
        if not existing_files:
            self.upload_status = "No existing files to process!"
            return

        for file_name in existing_files:
            file_path = upload_dir / file_name

            # Process and add to knowledge base
            app = self.get_app()
            app.add(str(file_path), data_type="pdf_file")
            self.knowledge_base_files.append(file_name)

        self.upload_status = f"Processed and added {len(existing_files)} existing file(s) to knowledge base!"

    def chat(self):
        if not self.user_question:
            return
        app = self.get_app()
        self.messages.append({"role": "user", "content": self.user_question})
        response = app.chat(self.user_question)
        self.messages.append({"role": "assistant", "content": response})
        self.user_question = ""  # Clear the question after sending

    def clear_chat(self):
        self.messages = []

    def set_user_question(self, value: str):
        self.user_question = value

color = "rgb(107,99,246)"

def index():
    return rx.vstack(
        rx.heading("Chat with PDF using Llama 3.2"),
        rx.text("This app allows you to chat with PDF using Llama 3.2 running locally with Ollama!"),
        rx.vstack(
            rx.heading("PDF Upload and Process", size="md"),
            rx.upload(
                rx.vstack(
                    rx.button(
                        "Select PDF Files",
                        color=color,
                        bg="white",
                        border=f"1px solid {color}",
                    ),
                    rx.text("Drag and drop PDF files here or click to select"),
                ),
                id="pdf_upload",
                multiple=True,
                accept={".pdf": "application/pdf"},
                max_files=10,
                border=f"1px dotted {color}",
                padding="2em",
            ),
            rx.hstack(rx.foreach(rx.selected_files("pdf_upload"), rx.text)),
            rx.button(
                "Upload and Process Files",
                on_click=State.upload_and_process_files(rx.upload_files(upload_id="pdf_upload")),
            ),
            rx.text(State.upload_status),  # Display upload status
            width="50%",
        ),
        rx.vstack(
            rx.foreach(
                State.messages,
                lambda message, index: rx.cond(
                    message["role"] == "user",
                    rx.box(
                        rx.text(message["content"]),
                        background_color="rgb(0,0,0)",
                        padding="10px",
                        border_radius="10px",
                        margin_y="5px",
                        width="100%",
                    ),
                    rx.box(
                        rx.text(message["content"]),
                        background_color="rgb(0,0,0)",
                        padding="10px",
                        border_radius="10px",
                        margin_y="5px",
                        width="100%",
                    ),
                )
            ),
            rx.hstack(
                rx.input(
                    placeholder="Ask a question about the PDFs",
                    id="user_question",
                    value=State.user_question,
                    on_change=lambda value: State.set_user_question(value),
                    **message_style,
                ),
                rx.button("Send Question", on_click=State.chat),
            ),
            rx.button("Clear Chat History", on_click=State.clear_chat),
            width="100%",
            height="100vh",
            overflow="auto",
        ),
        padding="2em",
    )

app = rx.App()

# Llamar a la función para procesar archivos existentes al cargar la página
app.add_page(index, on_load=State.process_existing_files)

