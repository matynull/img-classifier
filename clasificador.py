import os
import sys
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QCompleter, QMessageBox, QDialog, QPushButton,
                           QMenuBar, QAction, QFileDialog, QListWidget, QListWidgetItem, QProgressBar, QFrame)
from PyQt5.QtCore import Qt, QSize, QRect, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QIcon, QKeySequence
from PIL import Image
from pathlib import Path

class AutoCompleteLineEdit(QLineEdit):
    nextImageSignal = pyqtSignal()  # Nueva señal para siguiente imagen
    
    def __init__(self, completevalues, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._completer = None
        self._suggestion = ""
        self._last_category = ""  # Variable privada para la última categoría
        self._ejemplos_path = "ejemplos"  # Carpeta de ejemplos
        self._preview_label = None  # Label para mostrar la imagen de ejemplo
        self._last_shown_category = ""  # Última categoría mostrada en imagen de ejemplo
        self.textChanged.connect(self.updateSuggestion)
        self.setCompleter(completevalues)

    @property
    def last_category(self):
        return self._last_category

    @last_category.setter
    def last_category(self, value):
        if value:  # Solo guardar si no está vacío
            self._last_category = value
            self.setPlaceholderText(value)  # Actualizar el placeholder

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # Si el campo está vacío, usar el placeholder
            if not self.text() and self.placeholderText():
                self.setText(self.placeholderText())
            event.accept()
        elif event.key() == Qt.Key_Control:
            self.nextImageSignal.emit()  # Emitir señal para siguiente imagen
            event.accept()
            return
        super().keyPressEvent(event)

    def setCompleter(self, completevalues):
        completer = QCompleter(completevalues)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer = completer
        super().setCompleter(completer)

    def set_preview_label(self, label):
        """Establece el label donde mostrar las imágenes de ejemplo"""
        self._preview_label = label

    def get_ejemplo_path(self, categoria):
        """Obtiene la ruta de la imagen de ejemplo para una categoría"""
        if not categoria:
            return None
        extensiones = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
        for ext in extensiones:
            path = os.path.join(self._ejemplos_path, f"{categoria}{ext}")
            if os.path.exists(path):
                return path
        return None

    def updateSuggestion(self, text):
        """Busca la mejor sugerencia que empiece con el texto actual."""
        self._suggestion = ""
        if self._completer is not None and text:
            model = self._completer.completionModel()
            if model:
                for row in range(model.rowCount()):
                    idx = model.index(row, 0)
                    candidate = model.data(idx)
                    if candidate.lower().startswith(text.lower()):
                        self._suggestion = candidate
                        # Mostrar imagen de ejemplo si existe
                        self.show_example_image(candidate)
                        break
        else:
            # Si no hay texto, mantener la última imagen mostrada (no limpiar automáticamente)
            # Solo limpiar si no hay categoría previa mostrada
            if self._preview_label and not self._last_shown_category:
                self._preview_label.clear()
                self._preview_label.setText("Imagen de ejemplo")
        self.update()

    def show_example_image(self, categoria):
        """Muestra la imagen de ejemplo para la categoría dada"""
        if not self._preview_label:
            return
        
        ejemplo_path = self.get_ejemplo_path(categoria)
        if ejemplo_path and os.path.exists(ejemplo_path):
            try:
                pixmap = QPixmap(ejemplo_path)
                if not pixmap.isNull():
                    # Escalar la imagen manteniendo la proporción
                    scaled_pixmap = pixmap.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self._preview_label.setPixmap(scaled_pixmap)
                    self._preview_label.setText("")  # Limpiar texto
                    self._last_shown_category = categoria  # Guardar categoría mostrada
                else:
                    self._preview_label.clear()
                    self._preview_label.setText("Imagen no válida")
            except Exception as e:
                self._preview_label.clear()
                self._preview_label.setText("Error al cargar imagen")
        else:
            self._preview_label.clear()
            self._preview_label.setText("Sin ejemplo")

    def clear(self):
        """Sobreescribir clear para asegurar que el texto se limpia completamente"""
        super().clear()
        self.setText("")  # Forzar texto vacío
        # Mantener la imagen de ejemplo (no limpiar automáticamente)
        # La imagen se mantendrá hasta que se muestre una nueva categoría
        
    def clear_example_image(self):
        """Limpiar explícitamente la imagen de ejemplo cuando sea necesario"""
        self._last_shown_category = ""
        if self._preview_label:
            self._preview_label.clear()
            self._preview_label.setText("Imagen de ejemplo")
        
    def setText(self, text):
        """Sobreescribir setText para controlar el texto inicial"""
        if not text:  # Si el texto es vacío, asegurarse de que realmente esté vacío
            super().clear()
            super().setText("")
        else:
            super().setText(text)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._suggestion and self.text() and len(self._suggestion) > len(self.text()):
            # Calcular el ancho del texto actual
            fm = self.fontMetrics()
            text_width = fm.horizontalAdvance(self.text()) if hasattr(fm, 'horizontalAdvance') else fm.width(self.text())
            painter = QPainter(self)
            painter.setPen(Qt.gray)
            
            # Calcular la posición correcta para que esté alineado con el texto
            content_rect = self.contentsRect()
            x = content_rect.left() + text_width + 2
            
            # Usar la misma línea base que el texto principal
            y = content_rect.top() + fm.ascent() + (content_rect.height() - fm.height()) // 2
            
            # Dibujar la parte de la sugerencia que falta
            remaining = self._suggestion[len(self.text()):]
            painter.drawText(x, y, remaining)

class ImageLabel(QLabel):
    def __init__(self, size, parent=None, can_draw_bbox=True):
        super().__init__(parent)
        self.bbox = None
        self.original_size = None
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(QSize(size[0], size[1]))
        self.drawing = False
        self.start_point = None
        self.current_bbox = None
        self.can_draw_bbox = can_draw_bbox
        if can_draw_bbox:
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def set_bbox(self, bbox, original_size):
        self.bbox = bbox
        self.original_size = original_size
        self.update()

    def get_pixmap_rect(self):
        if not self.pixmap():
            return QRect()
        
        scaled_size = self.pixmap().size()
        scaled_size.scale(self.size(), Qt.KeepAspectRatio)
        
        x = (self.width() - scaled_size.width()) // 2
        y = (self.height() - scaled_size.height()) // 2
        
        return QRect(x, y, scaled_size.width(), scaled_size.height())

    def mousePressEvent(self, event):
        if not self.can_draw_bbox:
            return
        if event.button() == Qt.LeftButton and self.original_size:
            self.drawing = True
            pixmap_rect = self.get_pixmap_rect()
            if not pixmap_rect.contains(event.pos()):
                return
            
            # Calcular las escalas basadas en el tamaño real de la imagen
            scale_x = self.original_size[0] / pixmap_rect.width()
            scale_y = self.original_size[1] / pixmap_rect.height()
            
            # Convertir coordenadas del mouse a coordenadas de la imagen
            x = (event.pos().x() - pixmap_rect.x()) * scale_x
            y = (event.pos().y() - pixmap_rect.y()) * scale_y
            
            # Asegurarse de que las coordenadas estén dentro de los límites de la imagen
            x = max(0, min(x, self.original_size[0]))
            y = max(0, min(y, self.original_size[1]))
            
            self.start_point = (int(x), int(y))
            self.current_bbox = None
            self.update()

    def mouseMoveEvent(self, event):
        if not self.can_draw_bbox:
            return
        if self.drawing and self.start_point and self.original_size:
            pixmap_rect = self.get_pixmap_rect()
            if not pixmap_rect.contains(event.pos()):
                return
            
            # Calcular las escalas basadas en el tamaño real de la imagen
            scale_x = self.original_size[0] / pixmap_rect.width()
            scale_y = self.original_size[1] / pixmap_rect.height()
            
            # Convertir coordenadas del mouse a coordenadas de la imagen
            x = (event.pos().x() - pixmap_rect.x()) * scale_x
            y = (event.pos().y() - pixmap_rect.y()) * scale_y
            
            # Asegurarse de que las coordenadas estén dentro de los límites de la imagen
            x = max(0, min(x, self.original_size[0]))
            y = max(0, min(y, self.original_size[1]))
            
            x1 = min(self.start_point[0], int(x))
            x2 = max(self.start_point[0], int(x))
            y1 = min(self.start_point[1], int(y))
            y2 = max(self.start_point[1], int(y))
            
            # Asegurarse de que el bbox no exceda los límites de la imagen
            x1 = max(0, x1)
            x2 = min(self.original_size[0], x2)
            y1 = max(0, y1)
            y2 = min(self.original_size[1], y2)
            
            self.current_bbox = (x1, x2, y1, y2)
            self.update()

    def mouseReleaseEvent(self, event):
        if not self.can_draw_bbox:
            return
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            if self.current_bbox:
                # Asegurarse de que el bbox tenga un tamaño mínimo
                if (self.current_bbox[1] - self.current_bbox[0] > 5 and 
                    self.current_bbox[3] - self.current_bbox[2] > 5):
                    # Notificar al parent para mostrar el popup
                    parent = self.parent()
                    while parent and not isinstance(parent, ClasificadorImagenes):
                        parent = parent.parent()
                    if parent:
                        parent.show_classification_dialog(self.current_bbox)
            self.current_bbox = None
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.pixmap() or not self.original_size:
            return

        painter = QPainter(self)
        pen = QPen(QColor(255, 0, 0))
        pen.setWidth(1)
        painter.setPen(pen)

        pixmap_rect = self.get_pixmap_rect()
        scale_x = pixmap_rect.width() / self.original_size[0]
        scale_y = pixmap_rect.height() / self.original_size[1]

        # Dibujar el bbox original si existe
        if self.bbox:
            pen.setColor(QColor(255, 0, 0))
            painter.setPen(pen)
            x1 = pixmap_rect.x() + int(self.bbox[0] * scale_x)
            x2 = pixmap_rect.x() + int(self.bbox[1] * scale_x)
            y1 = pixmap_rect.y() + int(self.bbox[2] * scale_y)
            y2 = pixmap_rect.y() + int(self.bbox[3] * scale_y)
            painter.drawRect(x1, y1, x2 - x1, y2 - y1)

        # Dibujar el bbox actual si se está dibujando
        if self.current_bbox:
            pen.setColor(QColor(0, 255, 0))
            painter.setPen(pen)
            x1 = pixmap_rect.x() + int(self.current_bbox[0] * scale_x)
            x2 = pixmap_rect.x() + int(self.current_bbox[1] * scale_x)
            y1 = pixmap_rect.y() + int(self.current_bbox[2] * scale_y)
            y2 = pixmap_rect.y() + int(self.current_bbox[3] * scale_y)
            painter.drawRect(x1, y1, x2 - x1, y2 - y1)

class ClassificationDialog(QDialog):
    def __init__(self, categorias, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clasificar Región Seleccionada")
        self.setModal(True)
        self.categorias = categorias  # Guardar categorías para validación
        
        # Configurar el diálogo con estilo moderno
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                border-radius: 12px;
            }
            QLabel {
                font-size: 14px;
                color: #495057;
                background: none;
                border: none;
            }
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 6px;
                border: none;
                min-width: 100px;
            }
            QPushButton[primary="true"] {
                background-color: #007bff;
                color: white;
            }
            QPushButton[primary="true"]:hover {
                background-color: #0056b3;
            }
            QPushButton[primary="true"]:pressed {
                background-color: #004085;
            }
            QPushButton[secondary="true"] {
                background-color: #6c757d;
                color: white;
            }
            QPushButton[secondary="true"]:hover {
                background-color: #545b62;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Label de instrucción
        instruction_label = QLabel("Selecciona la categoría para la región marcada:")
        instruction_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #495057;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(instruction_label)
        
        # Campo de entrada con autocompletado mejorado
        self.entrada = AutoCompleteLineEdit(categorias)
        self.entrada.setStyleSheet("""
            QLineEdit {
                font-size: 14px;
                padding: 12px 15px;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                background-color: #ffffff;
                color: #495057;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #007bff;
                background-color: #f8f9ff;
            }
        """)
        self.entrada.setPlaceholderText("Escribe para buscar categorías...")
        self.entrada.returnPressed.connect(self.accept)
        layout.addWidget(self.entrada)
        
        # Espaciador
        layout.addSpacing(10)
        
        # Botones con estilo moderno
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setProperty("secondary", True)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addSpacing(10)
        
        self.ok_button = QPushButton("Aceptar")
        self.ok_button.setProperty("primary", True)
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
        
        # Dar foco al campo de entrada
        self.entrada.setFocus()

    def get_categoria(self):
        return self.entrada.text().strip()

    def accept(self):
        categoria = self.get_categoria()
        if not categoria:
            QMessageBox.warning(self, "Error", "Por favor ingrese una categoría")
            return
        if categoria not in self.categorias:
            QMessageBox.warning(self, "Error", "Categoría no válida. Debe estar en categorias.txt")
            return
        super().accept()

class ClasificadorImagenes(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clasificador de Especies Marinas")
        
        # Establecer icono de pececito para la ventana y barra de tareas
        self.configurar_icono_ventana()
        
        # Estilo moderno para la ventana principal
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QMenuBar {
                background-color: #ffffff;
                border-bottom: 1px solid #e9ecef;
                padding: 5px;
                font-size: 14px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #e9ecef;
            }
            QMenu {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #e9ecef;
            }
        """)
        
        # Obtener la resolución de la pantalla
        screen = QApplication.primaryScreen().geometry()
        window_width = int(screen.width() * 0.8)
        window_height = int(screen.height() * 0.8)
        self.setMinimumSize(window_width, window_height)
        
        # Variables de estado
        self.current_bbox = None
        self.bbox_counter = 0  # Contador para los nombres de las imágenes
        
        # Variables para estadísticas
        self.clasificacion_stats = {}  # Diccionario para contar clasificaciones por categoría
        self.total_clasificadas = 0
        
        # Crear el widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        layout = QVBoxLayout(central_widget)
        
        # Crear menú
        self.create_menu()
        
        # Obtener la resolución de la pantalla
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        screen_height = screen_size.height()

        # Ajustar tamaños según la resolución
        # Para 720p y resoluciones similares (1280x720, 1366x768)
        if screen_height <= 800:
            self.window_width = 1000
            self.window_height = 620
            self.container_width = 450
            self.image_size = (450, 350)
        # Para 1080p (1920x1080)
        elif screen_height <= 1080:
            self.window_width = 1500
            self.window_height = 950
            self.container_width = 700
            self.image_size = (700, 550)
        # Para 2K (2560x1440) o superior
        else:
            self.window_width = 1900
            self.window_height = 1250
            self.container_width = 900
            self.image_size = (900, 700)

        # Configurar la ventana
        self.setGeometry(100, 100, self.window_width, self.window_height)
        self.setFixedSize(self.window_width, self.window_height)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)

        # Cargar categorías
        self.categorias = self.cargar_categorias()
        if not self.categorias:
            QMessageBox.critical(self, "Error", "No se encontró el archivo de categorías o está vacío")
            sys.exit(1)

        # Obtener lista de imágenes
        self.imagenes = self.obtener_imagenes()
        if not self.imagenes:
            QMessageBox.critical(self, "Error", "No se encontraron imágenes en el directorio")
            sys.exit(1)

        # Cargar bounding boxes
        self.bboxes = self.cargar_bboxes()
        if not self.bboxes:
            QMessageBox.critical(self, "Error", "No se encontró el archivo bbox.txt o está vacío")
            sys.exit(1)

        self.imagen_actual_index = 0
        
        # Crear interfaz
        self.setup_ui()
        
        # Mostrar primera imagen
        self.mostrar_imagen_actual()

    def configurar_icono_ventana(self):
        """Configurar el icono de la ventana y barra de tareas"""
        # Lista de iconos a probar (en orden de preferencia)
        icon_files = ["pez_icono.ico", "pez_icono.png", "icono.png"]
        
        for icon_file in icon_files:
            # Probar primero la ruta relativa (para desarrollo)
            if os.path.exists(icon_file):
                self.setWindowIcon(QIcon(icon_file))
                return
            
            # Probar la ruta de recursos (para ejecutable PyInstaller)
            try:
                # PyInstaller crea una carpeta temporal y almacena la ruta en _MEIPASS
                base_path = sys._MEIPASS
                resource_path = os.path.join(base_path, icon_file)
                if os.path.exists(resource_path):
                    self.setWindowIcon(QIcon(resource_path))
                    return
            except Exception:
                # Si no es un ejecutable empaquetado, continuar
                pass
        
        # Si no se encuentra ningún icono, crear un icono por defecto
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(52, 152, 219))  # Azul océano
        self.setWindowIcon(QIcon(pixmap))

    def create_menu(self):
        """Crear menú de la aplicación"""
        menubar = self.menuBar()
        
        # Menú de herramientas
        tools_menu = menubar.addMenu('Herramientas')
        
        # Acción para cargar ejemplos
        cargar_ejemplos_action = QAction('Cargar Ejemplos', self)
        cargar_ejemplos_action.setStatusTip('Cargar imágenes de ejemplo para cada categoría')
        cargar_ejemplos_action.triggered.connect(self.cargar_ejemplos)
        tools_menu.addAction(cargar_ejemplos_action)

    def cargar_ejemplos(self):
        """Cargar imágenes de ejemplo para cada categoría"""
        # Crear carpeta de ejemplos si no existe
        ejemplos_path = "ejemplos"
        Path(ejemplos_path).mkdir(exist_ok=True)
        
        # Obtener categorías que no tienen ejemplo
        categorias_sin_ejemplo = []
        for categoria in self.categorias:
            tiene_ejemplo = False
            extensiones = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
            for ext in extensiones:
                ejemplo_path = os.path.join(ejemplos_path, f"{categoria}{ext}")
                if os.path.exists(ejemplo_path):
                    tiene_ejemplo = True
                    break
            if not tiene_ejemplo:
                categorias_sin_ejemplo.append(categoria)
        
        if not categorias_sin_ejemplo:
            QMessageBox.information(self, "Información", "Todas las categorías ya tienen imágenes de ejemplo.")
            return
        
        # Preguntar si desea cargar ejemplos para las categorías faltantes
        reply = QMessageBox.question(self, "Cargar Ejemplos", 
                                   f"Se encontraron {len(categorias_sin_ejemplo)} categorías sin imagen de ejemplo.\n"
                                   f"¿Desea cargar imágenes para estas categorías?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.cargar_ejemplos_categorias(categorias_sin_ejemplo, ejemplos_path)

    def cargar_ejemplos_categorias(self, categorias, ejemplos_path):
        """Cargar ejemplos para las categorías especificadas"""
        for i, categoria in enumerate(categorias):
            # Mostrar progreso
            progress_text = f"Cargando ejemplo para: {categoria} ({i+1}/{len(categorias)})"
            
            # Abrir diálogo para seleccionar imagen
            file_dialog = QFileDialog()
            file_dialog.setWindowTitle(f"Seleccionar imagen de ejemplo para: {categoria}")
            file_dialog.setNameFilter("Imágenes (*.png *.jpg *.jpeg *.bmp *.gif)")
            file_dialog.setFileMode(QFileDialog.ExistingFile)
            
            if file_dialog.exec_() == QFileDialog.Accepted:
                selected_files = file_dialog.selectedFiles()
                if selected_files:
                    source_path = selected_files[0]
                    # Obtener extensión del archivo original
                    _, ext = os.path.splitext(source_path)
                    # Crear ruta de destino
                    dest_path = os.path.join(ejemplos_path, f"{categoria}{ext}")
                    
                    try:
                        # Copiar imagen a la carpeta de ejemplos
                        shutil.copy2(source_path, dest_path)
                        
                        # Redimensionar imagen para optimizar espacio (opcional)
                        self.resize_example_image(dest_path)
                        
                    except Exception as e:
                        QMessageBox.warning(self, "Error", f"Error al copiar imagen para {categoria}: {str(e)}")
            else:
                # Si cancela, preguntar si desea continuar con las demás
                if i < len(categorias) - 1:  # Si no es la última categoría
                    reply = QMessageBox.question(self, "Continuar", 
                                               f"¿Desea continuar con las categorías restantes?",
                                               QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.No:
                        break
        
        QMessageBox.information(self, "Completado", "Proceso de carga de ejemplos completado.")

    def resize_example_image(self, image_path):
        """Redimensionar imagen de ejemplo para optimizar espacio"""
        try:
            with Image.open(image_path) as img:
                # Redimensionar manteniendo proporción, máximo 300x300
                img.thumbnail((300, 300), Image.LANCZOS)
                img.save(image_path, optimize=True, quality=85)
        except Exception as e:
            print(f"Error al redimensionar imagen {image_path}: {e}")

    def cargar_categorias(self):
        try:
            with open('categorias.txt', 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            return []

    def obtener_imagenes(self):
        # Asegurarse de que la carpeta 'photos' existe
        if not os.path.exists('photos'):
            QMessageBox.critical(self, "Error", "No se encontró la carpeta 'photos'")
            sys.exit(1)

        extensiones = ('.jpg', '.jpeg', '.png')
        return [f for f in os.listdir('photos') if f.lower().endswith(extensiones)]

    def cargar_bboxes(self):
        try:
            bboxes = {}
            with open('bbox.txt', 'r', encoding='utf-8') as f:
                for line in f:
                    # Dividir la línea en partes
                    parts = line.strip().split()
                    if len(parts) >= 6:
                        # Encontrar el índice donde comienzan las coordenadas (los últimos 4 números)
                        for i in range(len(parts)-4, -1, -1):
                            try:
                                # Intentar convertir los últimos 4 elementos a partir de i
                                coords = list(map(int, parts[i:i+4]))
                                if len(coords) == 4:
                                    # Si se convirtieron 4 números, tenemos las coordenadas
                                    # El nombre de la imagen es todo lo que está antes
                                    imagen_nombre = ' '.join(parts[:i-1])  # -1 para excluir la especie
                                    x1, x2, y1, y2 = coords
                                    bboxes[imagen_nombre] = (x1, x2, y1, y2)
                                    break
                            except ValueError:
                                continue
            return bboxes
        except FileNotFoundError:
            return {}

    def setup_ui(self):
        # Widget central con estilo moderno
        central_widget = QWidget()
        central_widget.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 15)

        # Layout horizontal para las imágenes
        images_layout = QHBoxLayout()
        images_layout.setSpacing(25)

        # Contenedor para la imagen original
        left_container = QWidget()
        left_container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                           stop:0 #ffffff, stop:1 #f8f9fa);
                border: 1px solid #dee2e6;
                border-radius: 10px;
                padding: 5px;
            }
        """)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(2, 2, 2, 2)
        
        # Título para la imagen original
        original_title = QLabel("Imagen Original")
        original_title.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: 600;
                color: #343a40;
                margin-bottom: 8px;
                background: none;
                border: none;
                letter-spacing: 0.5px;
            }
        """)
        original_title.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(original_title)
        
        # Label para la imagen original (puede dibujar bbox)
        self.label_imagen = ImageLabel(self.image_size, can_draw_bbox=True)
        self.label_imagen.setStyleSheet("""
            QLabel {
                border: none;
                background: transparent;
                margin: 0px;
                padding: 0px;
            }
        """)
        left_layout.addWidget(self.label_imagen)
        images_layout.addWidget(left_container)

        # Contenedor para la imagen con zoom
        right_container = QWidget()
        right_container.setFixedWidth(self.container_width)
        right_container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                           stop:0 #ffffff, stop:1 #f8f9fa);
                border: 1px solid #dee2e6;
                border-radius: 10px;
                padding: 5px;
            }
        """)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(2, 2, 2, 2)
        
        # Título para la imagen con zoom
        zoom_title = QLabel("Vista Detallada")
        zoom_title.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: 600;
                color: #343a40;
                margin-bottom: 8px;
                background: none;
                border: none;
                letter-spacing: 0.5px;
            }
        """)
        zoom_title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(zoom_title)
        
        # Label para la imagen con zoom (no puede dibujar bbox)
        self.label_zoom = ImageLabel(self.image_size, can_draw_bbox=False)
        self.label_zoom.setStyleSheet("""
            QLabel {
                border: none;
                background: transparent;
                margin: 0px;
                padding: 0px;
            }
        """)
        right_layout.addWidget(self.label_zoom)
        images_layout.addWidget(right_container)

        layout.addLayout(images_layout)

        # Layout horizontal para la entrada
        input_layout = QHBoxLayout()
        input_layout.setSpacing(25)
        
        # Contenedor para el campo de entrada
        input_widget = QWidget()
        input_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                           stop:0 #ffffff, stop:1 #f8f9fa);
                border: 1px solid #dee2e6;
                border-radius: 10px;
                padding: 12px;
            }
        """)
        input_container = QVBoxLayout(input_widget)
        input_container.setContentsMargins(12, 10, 12, 10)
        
        # Label para la entrada con estilo moderno
        categoria_label = QLabel("Categoría de la Especie")
        categoria_label.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: 600;
                color: #343a40;
                margin-bottom: 6px;
                background: none;
                border: none;
                letter-spacing: 0.3px;
            }
        """)
        input_container.addWidget(categoria_label)
        
        # Layout horizontal para entrada y navegación
        entrada_nav_layout = QHBoxLayout()
        entrada_nav_layout.setSpacing(8)
        
        # Botón anterior
        self.btn_anterior = QPushButton("◀")
        self.btn_anterior.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
                padding: 8px 12px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                background-color: #ffffff;
                color: #495057;
                min-width: 40px;
                max-width: 40px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
            QPushButton:disabled {
                background-color: #f8f9fa;
                color: #ced4da;
                border-color: #e9ecef;
            }
        """)
        self.btn_anterior.clicked.connect(self.imagen_anterior)
        entrada_nav_layout.addWidget(self.btn_anterior)
        
        # Campo de entrada con autocompletado mejorado (más ancho)
        self.entrada = AutoCompleteLineEdit(self.categorias)
        self.entrada.setStyleSheet("""
            QLineEdit {
                font-size: 15px;
                padding: 10px 15px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                background-color: #ffffff;
                color: #495057;
                min-height: 20px;
                font-weight: 500;
                min-width: 300px;
            }
            QLineEdit:focus {
                border-color: #0d6efd;
                background-color: #f8f9ff;
                outline: none;
                box-shadow: 0 0 0 2px rgba(13, 110, 253, 0.1);
            }
            QLineEdit:hover {
                border-color: #adb5bd;
            }
        """)
        self.entrada.setPlaceholderText("Escribe o selecciona una categoría...")
        self.entrada.returnPressed.connect(self.procesar_clasificacion)
        self.entrada.nextImageSignal.connect(self.siguiente_imagen)
        entrada_nav_layout.addWidget(self.entrada)
        
        # Botón siguiente
        self.btn_siguiente = QPushButton("▶")
        self.btn_siguiente.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
                padding: 8px 12px;
                border: 1px solid #ced4da;
                border-radius: 6px;
                background-color: #ffffff;
                color: #495057;
                min-width: 40px;
                max-width: 40px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
            QPushButton:disabled {
                background-color: #f8f9fa;
                color: #ced4da;
                border-color: #e9ecef;
            }
        """)
        self.btn_siguiente.clicked.connect(self.imagen_siguiente)
        entrada_nav_layout.addWidget(self.btn_siguiente)
        
        input_container.addLayout(entrada_nav_layout)
        
        # Separador visual
        separador = QFrame()
        separador.setFrameShape(QFrame.HLine)
        separador.setStyleSheet("""
            QFrame {
                color: #dee2e6;
                margin: 8px 0px;
            }
        """)
        input_container.addWidget(separador)
        
        # Estadísticas de clasificación (aesthetic)
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #495057;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                           stop:0 #e3f2fd, stop:1 #f3e5f5);
                border: 1px solid #bbdefb;
                border-radius: 6px;
                padding: 8px 12px;
                margin: 4px 0px;
                font-weight: 500;
            }
        """)
        self.stats_label.setAlignment(Qt.AlignCenter)
        input_container.addWidget(self.stats_label)
        
        # Añadir texto de ayuda
        help_text = QLabel("Enter: clasificar | Ctrl: saltar | ◀ ▶: navegar")
        help_text.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #6c757d;
                margin-top: 6px;
                font-style: italic;
                background: none;
                border: none;
                text-align: center;
            }
        """)
        help_text.setAlignment(Qt.AlignCenter)
        input_container.addWidget(help_text)
        
        input_layout.addWidget(input_widget)
        
        # Contenedor para imagen de ejemplo
        ejemplo_widget = QWidget()
        ejemplo_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                           stop:0 #ffffff, stop:1 #f8f9fa);
                border: 1px solid #dee2e6;
                border-radius: 10px;
                padding: 8px;
            }
        """)
        ejemplo_layout = QVBoxLayout(ejemplo_widget)
        ejemplo_layout.setContentsMargins(8, 8, 8, 8)
        
        # Título para imagen de ejemplo
        ejemplo_title = QLabel("Imagen de Ejemplo")
        ejemplo_title.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 600;
                color: #343a40;
                margin-bottom: 6px;
                background: none;
                border: none;
                letter-spacing: 0.3px;
            }
        """)
        ejemplo_title.setAlignment(Qt.AlignCenter)
        ejemplo_layout.addWidget(ejemplo_title)
        
        # Label para mostrar imagen de ejemplo
        self.label_ejemplo = QLabel()
        self.label_ejemplo.setFixedSize(280, 280)
        self.label_ejemplo.setAlignment(Qt.AlignCenter)
        self.label_ejemplo.setStyleSheet("""
            QLabel {
                border: 2px dashed #dee2e6;
                border-radius: 8px;
                background-color: #f8f9fa;
                color: #6c757d;
                font-size: 14px;
            }
        """)
        self.label_ejemplo.setText("Imagen de ejemplo")
        ejemplo_layout.addWidget(self.label_ejemplo)
        
        input_layout.addWidget(ejemplo_widget)
        
        # Conectar el label de ejemplo con el campo de entrada
        self.entrada.set_preview_label(self.label_ejemplo)
        
        layout.addLayout(input_layout)

        # Barra de estado inferior moderna
        bottom_widget = QWidget()
        bottom_widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 10px 15px;
                margin-top: 10px;
            }
        """)
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setSpacing(15)
        bottom_layout.setContentsMargins(15, 10, 15, 10)

        # Barra de progreso visual (aesthetic)
        progress_container = QVBoxLayout()
        progress_container.setSpacing(5)
        
        # Label del progreso (texto a la izquierda)
        self.label_progreso = QLabel()
        self.label_progreso.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: #495057;
                background: none;
                border: none;
                padding: 2px 0px;
            }
        """)
        self.label_progreso.setAlignment(Qt.AlignLeft)
        progress_container.addWidget(self.label_progreso)
        
        # Barra de progreso visual (más sutil)
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e9ecef;
                border-radius: 4px;
                background-color: #f8f9fa;
                text-align: center;
                font-size: 10px;
                font-weight: 400;
                color: #6c757d;
                height: 12px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                           stop:0 #e3f2fd, stop:0.5 #bbdefb, stop:1 #90caf9);
                border-radius: 3px;
                margin: 1px;
            }
        """)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_container.addWidget(self.progress_bar)
        
        bottom_layout.addLayout(progress_container)

        # Separador visual
        separator = QLabel("|")
        separator.setStyleSheet("""
            QLabel {
                color: #dee2e6;
                font-size: 16px;
                background: none;
                border: none;
            }
        """)
        separator.setAlignment(Qt.AlignCenter)
        bottom_layout.addWidget(separator)

        # Label para el nombre de la imagen con estilo moderno
        self.label_nombre_imagen = QLabel()
        self.label_nombre_imagen.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #6c757d;
                background: none;
                border: none;
                font-family: 'Courier New', monospace;
                padding: 5px 10px;
                background-color: #f8f9fa;
                border-radius: 6px;
            }
        """)
        self.label_nombre_imagen.setAlignment(Qt.AlignRight)
        bottom_layout.addWidget(self.label_nombre_imagen)

        layout.addWidget(bottom_widget)

    def mostrar_imagen_actual(self):
        if self.imagen_actual_index >= len(self.imagenes):
            QMessageBox.information(self, "Completado", "¡Has clasificado todas las imágenes!")
            self.close()
            return

        # Limpiar el campo de entrada ANTES de cualquier otra operación
        self.entrada.blockSignals(True)
        self.entrada.clear()
        self.entrada.setText("")  # Forzar texto vacío
        self.entrada.clear_example_image()  # Limpiar imagen de ejemplo al cargar nueva imagen
        self.entrada.blockSignals(False)

        # Actualizar etiqueta de progreso con iconos
        progreso_actual = self.imagen_actual_index + 1
        total_imagenes = len(self.imagenes)
        porcentaje = (progreso_actual / total_imagenes) * 100
        
        self.label_progreso.setText(
            f"Progreso: {progreso_actual}/{total_imagenes} ({porcentaje:.1f}%)"
        )
        
        # Actualizar barra de progreso visual
        self.progress_bar.setValue(int(porcentaje))
        self.progress_bar.setFormat(f"{progreso_actual}/{total_imagenes}")
        
        # Actualizar estadísticas
        self.actualizar_estadisticas()
        
        # Actualizar estado de botones de navegación
        self.btn_anterior.setEnabled(self.imagen_actual_index > 0)
        self.btn_siguiente.setEnabled(self.imagen_actual_index < len(self.imagenes) - 1)

        # Cargar y mostrar imagen
        imagen_nombre = self.imagenes[self.imagen_actual_index]
        imagen_path = os.path.join('photos', imagen_nombre)
        
        # Mostrar el nombre de la imagen
        self.label_nombre_imagen.setText(imagen_nombre)
        imagen = Image.open(imagen_path)
        
        # Guardar tamaño original
        original_size = imagen.size

        # Ajustar el tamaño del contenedor si la imagen es más pequeña
        if original_size[0] < self.image_size[0] and original_size[1] < self.image_size[1]:
            # La imagen es más pequeña que el tamaño mínimo, ajustar el contenedor
            self.label_imagen.setMinimumSize(QSize(original_size[0], original_size[1]))
            self.label_imagen.setMaximumSize(QSize(original_size[0], original_size[1]))
            # Ajustar el contenedor izquierdo
            left_container = self.label_imagen.parent()
            left_container.setFixedWidth(original_size[0])
        else:
            # La imagen es más grande, usar el tamaño predefinido
            self.label_imagen.setMinimumSize(QSize(self.image_size[0], self.image_size[1]))
            self.label_imagen.setMaximumSize(QSize(self.image_size[0], self.image_size[1]))
            # Restaurar el tamaño del contenedor izquierdo
            left_container = self.label_imagen.parent()
            left_container.setFixedWidth(self.container_width)

        # Redimensionar imagen manteniendo proporción
        display_size = self.image_size
        imagen.thumbnail(display_size, Image.LANCZOS)
        
        # Convertir imagen de PIL a QPixmap
        imagen_path_temp = "temp_image.png"
        imagen.save(imagen_path_temp)
        pixmap = QPixmap(imagen_path_temp)
        
        # Mostrar imagen original
        self.label_imagen.setPixmap(pixmap)
        self.label_imagen.set_bbox(None, original_size)  # Establecer original_size incluso si no hay bbox
        
        # Establecer bounding box si existe
        if imagen_nombre in self.bboxes:
            bbox = self.bboxes[imagen_nombre]
            self.label_imagen.set_bbox(bbox, original_size)
            
            # Crear imagen recortada para el zoom
            imagen_original = Image.open(imagen_path)
            x1, x2, y1, y2 = bbox
            # Añadir un margen del 10% alrededor del bbox
            margin_x = int((x2 - x1) * 0.1)
            margin_y = int((y2 - y1) * 0.1)
            crop_x1 = max(0, x1 - margin_x)
            crop_x2 = min(imagen_original.size[0], x2 + margin_x)
            crop_y1 = max(0, y1 - margin_y)
            crop_y2 = min(imagen_original.size[1], y2 + margin_y)
            
            # Recortar la imagen
            imagen_recortada = imagen_original.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            
            # Calcular el factor de escala para que la imagen recortada ocupe todo el espacio disponible
            crop_width = crop_x2 - crop_x1
            crop_height = crop_y2 - crop_y1
            scale_x = display_size[0] / crop_width
            scale_y = display_size[1] / crop_height
            scale_factor = min(scale_x, scale_y)
            
            # Aplicar el zoom
            new_size = (
                int(crop_width * scale_factor),
                int(crop_height * scale_factor)
            )
            imagen_recortada = imagen_recortada.resize(new_size, Image.LANCZOS)
            
            # Guardar y mostrar imagen recortada
            imagen_recortada.save("temp_zoom.png")
            pixmap_zoom = QPixmap("temp_zoom.png")
            self.label_zoom.setPixmap(pixmap_zoom)
            self.label_zoom.set_bbox(None, (crop_width, crop_height))  # Establecer original_size para el zoom
        else:
            QMessageBox.warning(self, "Advertencia", f"No se encontró bounding box para la imagen: {imagen_nombre}")
            self.label_zoom.setPixmap(QPixmap())  # Limpiar imagen de zoom
            self.label_zoom.set_bbox(None, None)  # Limpiar bbox y original_size
        
        os.remove(imagen_path_temp)
        
        # Dar foco al campo de entrada
        self.entrada.setFocus()

    def keyPressEvent(self, event):
        """Manejar eventos de teclado para navegación"""
        if event.key() == Qt.Key_Left:
            # Tecla izquierda - imagen anterior
            self.imagen_anterior()
        elif event.key() == Qt.Key_Right:
            # Tecla derecha - imagen siguiente
            self.imagen_siguiente()
        else:
            # Pasar el evento al handler por defecto
            super().keyPressEvent(event)

    def procesar_clasificacion(self):
        categoria = self.entrada.text().strip()
        if not categoria:
            return

        if categoria not in self.categorias:
            QMessageBox.warning(self, "Error", "Categoría no válida")
            return

        # Guardar la categoría antes de clasificar
        self.entrada.last_category = categoria
        self.clasificar_imagen(categoria)

    def siguiente_imagen(self):
        """Mueve la imagen actual a la carpeta skip y avanza a la siguiente"""
        if self.imagen_actual_index >= len(self.imagenes):
            return

        imagen_nombre = self.imagenes[self.imagen_actual_index]
        imagen_path = os.path.join('photos', imagen_nombre)
        
        # Crear directorio skip si no existe
        skip_dir = "skip"
        Path(skip_dir).mkdir(exist_ok=True)

        # Mover imagen a la carpeta skip
        try:
            shutil.move(imagen_path, os.path.join(skip_dir, imagen_nombre))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al mover la imagen a skip: {str(e)}")
            return

        self.imagen_actual_index += 1
        self.mostrar_imagen_actual()

    def clasificar_imagen(self, categoria):
        if self.imagen_actual_index >= len(self.imagenes):
            return

        imagen_nombre = self.imagenes[self.imagen_actual_index]
        imagen_path = os.path.join('photos', imagen_nombre)

        # Crear directorio si no existe
        Path(categoria).mkdir(exist_ok=True)

        # Guardar la última categoría usada
        self.entrada.last_category = categoria
        
        # Actualizar estadísticas
        if categoria in self.clasificacion_stats:
            self.clasificacion_stats[categoria] += 1
        else:
            self.clasificacion_stats[categoria] = 1
        self.total_clasificadas += 1

        try:
            # Obtener bbox de la imagen antes de moverla
            bbox_info = None
            if imagen_nombre in self.bboxes:
                bbox_info = self.bboxes[imagen_nombre]

            # Mover la imagen
            shutil.move(imagen_path, os.path.join(categoria, imagen_nombre))
            
            # Si hay información de bbox, guardarla en el archivo bbox de la categoría
            if bbox_info:
                bbox_path = os.path.join(categoria, 'bbox.txt')
                with open(bbox_path, 'a', encoding='utf-8') as f:
                    # Escribir en el mismo formato que el archivo bbox original
                    x1, x2, y1, y2 = bbox_info
                    f.write(f"{imagen_nombre} {categoria} {x1} {x2} {y1} {y2}\n")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al mover la imagen: {str(e)}")
            return

        # Asegurarse de que el input esté vacío antes de pasar a la siguiente imagen
        self.entrada.blockSignals(True)
        self.entrada.clear()
        self.entrada.blockSignals(False)

        self.imagen_actual_index += 1
        self.mostrar_imagen_actual()

    def imagen_anterior(self):
        """Navega a la imagen anterior"""
        if self.imagen_actual_index > 0:
            self.imagen_actual_index -= 1
            self.mostrar_imagen_actual()

    def imagen_siguiente(self):
        """Navega a la imagen siguiente"""
        if self.imagen_actual_index < len(self.imagenes) - 1:
            self.imagen_actual_index += 1
            self.mostrar_imagen_actual()

    def actualizar_estadisticas(self):
        """Actualiza las estadísticas de clasificación de forma aesthetic y ordenada"""
        if not self.clasificacion_stats:
            self.stats_label.setText("📋 Aún no hay clasificaciones realizadas")
            return
        
        # Obtener top 3 categorías más clasificadas
        top_categorias = sorted(self.clasificacion_stats.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Formatear estadísticas de manera más ordenada
        total_text = f"Total: {self.total_clasificadas}"
        
        if top_categorias:
            # Formatear top categorías de manera más clara
            if len(top_categorias) == 1:
                top_text = f"Top: {top_categorias[0][0]} ({top_categorias[0][1]})"
            elif len(top_categorias) == 2:
                top_text = f"Top: {top_categorias[0][0]} ({top_categorias[0][1]}) • {top_categorias[1][0]} ({top_categorias[1][1]})"
            else:
                top_text = f"Top: {top_categorias[0][0]} ({top_categorias[0][1]}) • {top_categorias[1][0]} ({top_categorias[1][1]}) • {top_categorias[2][0]} ({top_categorias[2][1]})"
            
            stats_text = f"{total_text}  |  {top_text}"
        else:
            stats_text = total_text
        
        self.stats_label.setText(stats_text)

    def show_classification_dialog(self, bbox):
        """Muestra el diálogo para clasificar el bounding box"""
        if not hasattr(self, 'categorias'):
            self.categorias = self.obtener_categorias()
        
        dialog = ClassificationDialog(self.categorias, self)
        if dialog.exec_() == QDialog.Accepted:
            categoria = dialog.get_categoria()
            if categoria:
                self.clasificar_bbox(bbox, categoria)
                # Limpiar el bbox actual
                self.current_bbox = None
                # Encontrar el widget de imagen correcto
                for child in self.findChildren(ImageLabel):
                    child.current_bbox = None
                    child.update()
                    break

    def clasificar_bbox(self, bbox, categoria):
        """Clasifica un bounding box dibujado por el usuario"""
        if not bbox:
            return

        # Obtener la imagen actual
        imagen_actual = self.imagenes[self.imagen_actual_index]
        imagen_path = os.path.join('photos', imagen_actual)
        
        # Crear el nombre base de la imagen (sin extensión)
        nombre_base = os.path.splitext(imagen_actual)[0]
        extension = os.path.splitext(imagen_actual)[1]
        
        # Crear el nuevo nombre con el contador
        nuevo_nombre = f"{nombre_base}_{self.bbox_counter}{extension}"
        self.bbox_counter += 1  # Incrementar el contador
        
        # Actualizar estadísticas
        if categoria in self.clasificacion_stats:
            self.clasificacion_stats[categoria] += 1
        else:
            self.clasificacion_stats[categoria] = 1
        self.total_clasificadas += 1
        
        # Crear la carpeta de la categoría si no existe
        if not os.path.exists(categoria):
            os.makedirs(categoria)
        
        # Copiar la imagen a la carpeta de la categoría con el nuevo nombre
        shutil.copy2(imagen_path, os.path.join(categoria, nuevo_nombre))
        
        # Guardar la información del bbox en el archivo bbox.txt
        bbox_path = os.path.join(categoria, 'bbox.txt')
        with open(bbox_path, 'a', encoding='utf-8') as f:
            x1, x2, y1, y2 = bbox
            f.write(f"{nuevo_nombre} {categoria} {x1} {x2} {y1} {y2}\n")

        self.current_bbox = None

def main():
    app = QApplication(sys.argv)
    window = ClasificadorImagenes()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 