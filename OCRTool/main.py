"""
OCR Tool - Modern Desktop Application for Text Extraction
Supports JPEG, PNG, WebP, and PDF files with parallel processing
"""

import sys
import os
import io
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
import traceback

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QRadioButton, QButtonGroup,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QObject, QRunnable, QThreadPool, QSize
)
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QPalette, QColor

import pytesseract
from PIL import Image
import fitz  # PyMuPDF


# ==================== Portable Tesseract Setup ====================
def setup_tesseract_path():
    """Configure pytesseract to use bundled Tesseract when running as frozen executable"""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running as script (for development)
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    tesseract_path = os.path.join(base_path, 'tesseract', 'tesseract.exe')
    tessdata_path = os.path.join(base_path, 'tesseract', 'tessdata')
    
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        os.environ['TESSDATA_PREFIX'] = tessdata_path

# Initialize Tesseract path (must be called before any OCR operations)
setup_tesseract_path()


# ==================== Worker Signals ====================
class WorkerSignals(QObject):
    """Signals for worker threads to communicate with main thread"""
    finished = pyqtSignal(str, str)  # filename, extracted_text
    error = pyqtSignal(str, str)  # filename, error_message
    progress = pyqtSignal(int)  # progress increment


# ==================== OCR Worker ====================
class OCRWorker(QRunnable):
    """Worker thread for processing individual files with OCR"""
    
    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self.signals = WorkerSignals()
        
    def run(self):
        """Execute OCR processing on the file"""
        try:
            filename = os.path.basename(self.file_path)
            file_ext = Path(self.file_path).suffix.lower()
            
            # Check if Tesseract is available
            try:
                pytesseract.get_tesseract_version()
            except Exception:
                self.signals.error.emit(
                    filename,
                    "Tesseract OCR not found. Please install Tesseract and add it to your PATH."
                )
                return
            
            extracted_text = ""
            
            if file_ext == '.pdf':
                # Process PDF with incremental page handling for memory efficiency
                extracted_text = self._process_pdf(self.file_path)
            else:
                # Process image file
                extracted_text = self._process_image(self.file_path)
            
            self.signals.finished.emit(filename, extracted_text)
            self.signals.progress.emit(1)
            
        except Exception as e:
            filename = os.path.basename(self.file_path)
            self.signals.error.emit(filename, f"Error processing file: {str(e)}")
            self.signals.progress.emit(1)
    
    def _process_pdf(self, pdf_path: str) -> str:
        """Process PDF file page by page (memory efficient)"""
        text_parts = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                img_data = pix.tobytes("png")
                
                # Process with Tesseract
                image = Image.open(io.BytesIO(img_data))
                text = pytesseract.image_to_string(image, lang='eng')
                text_parts.append(text)
                
                # Release memory
                del pix
                del image
            
            doc.close()
            
        except Exception as e:
            raise Exception(f"PDF processing error: {str(e)}")
        
        return "\n".join(text_parts)
    
    def _process_image(self, image_path: str) -> str:
        """Process image file with Tesseract OCR"""
        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang='eng')
            return text
        except Exception as e:
            raise Exception(f"Image processing error: {str(e)}")


# ==================== Main Window ====================
class OCRMainWindow(QMainWindow):
    """Main application window with modern UI"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OCR Tool - Text Extraction")
        self.setMinimumSize(QSize(700, 500))
        
        # State variables
        self.dropped_files: List[str] = []
        self.results: Dict[str, str] = {}  # filename -> extracted text
        self.total_files = 0
        self.completed_files = 0
        self.output_file_path = ""
        self.output_folder_path = ""
        
        # Thread pool for parallel processing
        self.thread_pool = QThreadPool()
        
        # Setup UI
        self._setup_ui()
        self._apply_modern_style()
        
    def _setup_ui(self):
        """Create and arrange UI elements"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title_label = QLabel("OCR Text Extraction Tool")
        title_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2C3E50; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        # Drop zone and browse button layout
        input_layout = QHBoxLayout()
        input_layout.setSpacing(15)
        
        # Drop zone
        self.drop_zone = QLabel("Drag & Drop Files Here\n\nSupported: JPEG, PNG, WebP, PDF")
        self.drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_zone.setMinimumHeight(200)
        self.drop_zone.setFont(QFont("Segoe UI", 14))
        self.drop_zone.setStyleSheet("""
            QLabel {
                border: 3px dashed #4A90E2;
                border-radius: 15px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #F0F4F8, stop:1 #E1E8ED);
                color: #4A90E2;
                padding: 20px;
            }
        """)
        self.drop_zone.setAcceptDrops(True)
        self.drop_zone.dragEnterEvent = self.drag_enter_event
        self.drop_zone.dropEvent = self.drop_event
        input_layout.addWidget(self.drop_zone, 3)
        
        # Browse for input files button
        self.browse_input_btn = QPushButton("📂 Browse Files")
        self.browse_input_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.browse_input_btn.setMinimumHeight(200)
        self.browse_input_btn.setMinimumWidth(150)
        self.browse_input_btn.clicked.connect(self.browse_input_files)
        input_layout.addWidget(self.browse_input_btn, 1)
        
        main_layout.addLayout(input_layout)
        
        # Output mode selection
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Output Mode:")
        mode_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        mode_label.setStyleSheet("color: #2C3E50;")
        mode_layout.addWidget(mode_label)
        
        self.radio_combined = QRadioButton("Combined (Single File)")
        self.radio_separate = QRadioButton("Separate (Multiple Files)")
        self.radio_combined.setChecked(True)
        self.radio_combined.setFont(QFont("Segoe UI", 11))
        self.radio_separate.setFont(QFont("Segoe UI", 11))
        self.radio_combined.setStyleSheet("color: #2C3E50;")
        self.radio_separate.setStyleSheet("color: #2C3E50;")
        
        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.radio_combined)
        self.mode_group.addButton(self.radio_separate)
        
        mode_layout.addWidget(self.radio_combined)
        mode_layout.addWidget(self.radio_separate)
        mode_layout.addStretch()
        main_layout.addLayout(mode_layout)
        
        # Output destination selection
        output_layout = QHBoxLayout()
        output_layout.setSpacing(10)
        
        output_label = QLabel("Output Destination:")
        output_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        output_label.setStyleSheet("color: #2C3E50;")
        output_layout.addWidget(output_label)
        
        self.output_path_label = QLabel("Not selected")
        self.output_path_label.setFont(QFont("Segoe UI", 11))
        self.output_path_label.setStyleSheet("color: #7F8C8D; font-style: italic;")
        output_layout.addWidget(self.output_path_label, 1)
        
        self.browse_output_btn = QPushButton("📁 Browse")
        self.browse_output_btn.setFont(QFont("Segoe UI", 11))
        self.browse_output_btn.setMinimumHeight(40)
        self.browse_output_btn.setMinimumWidth(120)
        self.browse_output_btn.clicked.connect(self.browse_output_destination)
        output_layout.addWidget(self.browse_output_btn)
        
        main_layout.addLayout(output_layout)
        
        # Status label
        self.status_label = QLabel("Ready to process files")
        self.status_label.setFont(QFont("Segoe UI", 11))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #34495E; padding: 5px;")
        main_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setFont(QFont("Segoe UI", 10))
        self.progress_bar.setTextVisible(True)
        main_layout.addWidget(self.progress_bar)
        
    def _apply_modern_style(self):
        """Apply modern styling to the application"""
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #FFFFFF, stop:1 #F5F7FA);
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #5DA3FA, stop:1 #4A90E2);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #6DB0FF, stop:1 #5DA3FA);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                           stop:0 #4A90E2, stop:1 #3A7BC8);
            }
            QProgressBar {
                border: 2px solid #4A90E2;
                border-radius: 8px;
                text-align: center;
                background: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #4A90E2, stop:1 #5DA3FA);
                border-radius: 6px;
            }
            QRadioButton {
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        
    def drag_enter_event(self, event: QDragEnterEvent):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_zone.setStyleSheet("""
                QLabel {
                    border: 3px dashed #2ECC71;
                    border-radius: 15px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                               stop:0 #E8F8F5, stop:1 #D5F4E6);
                    color: #2ECC71;
                    padding: 20px;
                }
            """)
    
    def drop_event(self, event: QDropEvent):
        """Handle drop event"""
        # Reset drop zone style
        self.drop_zone.setStyleSheet("""
            QLabel {
                border: 3px dashed #4A90E2;
                border-radius: 15px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #F0F4F8, stop:1 #E1E8ED);
                color: #4A90E2;
                padding: 20px;
            }
        """)
        
        files = []
        supported_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.pdf'}
        
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                ext = Path(file_path).suffix.lower()
                if ext in supported_extensions:
                    files.append(file_path)
                else:
                    self.show_toast(
                        "Unsupported File",
                        f"File type '{ext}' not supported: {os.path.basename(file_path)}",
                        QMessageBox.Icon.Warning
                    )
        
        if files:
            self.dropped_files = files
            self.process_files()
        else:
            self.show_toast(
                "No Valid Files",
                "Please drop supported files (JPEG, PNG, WebP, PDF)",
                QMessageBox.Icon.Warning
            )
    
    def browse_input_files(self):
        """Open file dialog for selecting input files"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files to Process",
            "",
            "Supported Files (*.jpg *.jpeg *.png *.webp *.pdf);;All Files (*.*)"
        )
        if files:
            self.dropped_files = files
            self.status_label.setText(f"Selected {len(files)} file(s)")
            self.process_files()
    
    def browse_output_destination(self):
        """Open dialog for selecting output destination based on mode"""
        is_combined = self.radio_combined.isChecked()
        
        if is_combined:
            # Browse for output file
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Select Output File",
                "OCR_output.txt",
                "Text Files (*.txt)"
            )
            if file_path:
                if not file_path.endswith('.txt'):
                    file_path += '.txt'
                self.output_file_path = file_path
                self.output_folder_path = ""
                self.output_path_label.setText(os.path.basename(file_path))
                self.output_path_label.setStyleSheet("color: #2C3E50;")
        else:
            # Browse for output folder
            folder_path = QFileDialog.getExistingDirectory(
                self,
                "Select Output Folder"
            )
            if folder_path:
                self.output_folder_path = folder_path
                self.output_file_path = ""
                self.output_path_label.setText(folder_path)
                self.output_path_label.setStyleSheet("color: #2C3E50;")
    
    def process_files(self):
        """Start parallel processing of dropped files"""
        if not self.dropped_files:
            return
        
        # Check if output location is set
        is_combined = self.radio_combined.isChecked()
        if is_combined and not self.output_file_path:
            self.show_toast(
                "Output Location Required",
                "Please select an output file location first",
                QMessageBox.Icon.Warning
            )
            return
        elif not is_combined and not self.output_folder_path:
            self.show_toast(
                "Output Location Required",
                "Please select an output folder first",
                QMessageBox.Icon.Warning
            )
            return
        
        # Reset state
        self.results.clear()
        self.total_files = len(self.dropped_files)
        self.completed_files = 0
        self.progress_bar.setMaximum(self.total_files)
        self.progress_bar.setValue(0)
        
        self.status_label.setText(f"Processing {self.total_files} file(s)...")
        
        # Create and start workers for parallel processing
        for file_path in self.dropped_files:
            worker = OCRWorker(file_path)
            worker.signals.finished.connect(self.on_worker_finished)
            worker.signals.error.connect(self.on_worker_error)
            worker.signals.progress.connect(self.on_worker_progress)
            self.thread_pool.start(worker)
    
    def on_worker_finished(self, filename: str, text: str):
        """Handle successful OCR completion"""
        self.results[filename] = text
    
    def on_worker_error(self, filename: str, error_msg: str):
        """Handle OCR error"""
        self.show_toast(
            f"Error: {filename}",
            error_msg,
            QMessageBox.Icon.Critical
        )
    
    def on_worker_progress(self, increment: int):
        """Update progress bar"""
        self.completed_files += increment
        self.progress_bar.setValue(self.completed_files)
        
        if self.completed_files >= self.total_files:
            # All files processed
            self.save_results()
    
    def save_results(self):
        """Save extracted text to file(s)"""
        if not self.results:
            self.status_label.setText("No text extracted")
            return
        
        try:
            is_combined = self.radio_combined.isChecked()
            
            if is_combined:
                # Save all results to single file
                combined_text = "\n\n".join(self.results.values())
                with open(self.output_file_path, 'w', encoding='utf-8') as f:
                    f.write(combined_text)
                
                self.status_label.setText(f"✓ Saved to {os.path.basename(self.output_file_path)}")
                self.show_toast(
                    "Success",
                    f"Text extracted from {len(self.results)} file(s)\nSaved to: {self.output_file_path}",
                    QMessageBox.Icon.Information
                )
            else:
                # Save separate files
                saved_count = 0
                for filename, text in self.results.items():
                    base_name = Path(filename).stem
                    output_path = os.path.join(self.output_folder_path, f"{base_name}.txt")
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(text)
                    saved_count += 1
                
                self.status_label.setText(f"✓ Saved {saved_count} file(s)")
                self.show_toast(
                    "Success",
                    f"Text extracted from {saved_count} file(s)\nSaved to: {self.output_folder_path}",
                    QMessageBox.Icon.Information
                )
            
        except Exception as e:
            self.show_toast(
                "Save Error",
                f"Failed to save results: {str(e)}",
                QMessageBox.Icon.Critical
            )
    
    def show_toast(self, title: str, message: str, icon: QMessageBox.Icon):
        """Display toast notification"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()


# ==================== Main Entry Point ====================
def main():
    """Application entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern cross-platform style
    
    window = OCRMainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
