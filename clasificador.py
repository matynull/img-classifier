import os
import sys
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QCompleter, QMessageBox, QDialog, QPushButton)
from PyQt5.QtCore import Qt, QSize, QRect, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QIcon
from PIL import Image
from pathlib import Path

class AutoCompleteLineEdit(QLineEdit):
    nextImageSignal = pyqtSignal()  # Nueva señal para siguiente imagen
    
    def __init__(self, completevalues, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._completer = None
        self._suggestion = ""
        self._last_category = ""  # Variable privada para la última categoría
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
                        break
        self.update()

    def clear(self):
        """Sobreescribir clear para asegurar que el texto se limpia completamente"""
        super().clear()
        self.setText("")  # Forzar texto vacío
        
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
            text_width = fm.width(self.text())
            painter = QPainter(self)
            painter.setPen(Qt.gray)
            # Calcular la posición en base a los márgenes del QLineEdit
            x = self.contentsRect().left() + text_width + 2
            # La posición vertical se alinea con la línea base del texto
            y = self.contentsRect().bottom() - fm.descent()
            # Dibujar la parte de la sugerencia que falta
            remaining = self._suggestion[len(self.text()):]
            painter.drawText(x, y, remaining)

class ImageLabel(QLabel):
    def __init__(self, size, parent=None):
        super().__init__(parent)
        self.bbox = None
        self.original_size = None
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(QSize(size[0], size[1]))
        self.drawing = False
        self.start_point = None
        self.current_bbox = None
        self.setCursor(Qt.CrossCursor)  # Cambiar el cursor para indicar que se puede dibujar

    def set_bbox(self, bbox, original_size):
        self.bbox = bbox
        self.original_size = original_size
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            # Convertir coordenadas de pantalla a coordenadas de imagen
            pixmap_rect = self.get_pixmap_rect()
            if not pixmap_rect.contains(event.pos()):
                return
            
            # Calcular las escalas
            scale_x = self.original_size[0] / pixmap_rect.width()
            scale_y = self.original_size[1] / pixmap_rect.height()
            
            # Convertir coordenadas
            x = (event.pos().x() - pixmap_rect.x()) * scale_x
            y = (event.pos().y() - pixmap_rect.y()) * scale_y
            
            self.start_point = (int(x), int(y))
            self.current_bbox = None
            self.update()

    def mouseMoveEvent(self, event):
        if self.drawing and self.start_point:
            pixmap_rect = self.get_pixmap_rect()
            if not pixmap_rect.contains(event.pos()):
                return
            
            # Calcular las escalas
            scale_x = self.original_size[0] / pixmap_rect.width()
            scale_y = self.original_size[1] / pixmap_rect.height()
            
            # Convertir coordenadas
            x = (event.pos().x() - pixmap_rect.x()) * scale_x
            y = (event.pos().y() - pixmap_rect.y()) * scale_y
            
            x1 = min(self.start_point[0], int(x))
            x2 = max(self.start_point[0], int(x))
            y1 = min(self.start_point[1], int(y))
            y2 = max(self.start_point[1], int(y))
            self.current_bbox = (x1, x2, y1, y2)
            self.update()

    def mouseReleaseEvent(self, event):
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
        pen = QPen(QColor(255, 0, 0))  # Color rojo
        pen.setWidth(1)
        painter.setPen(pen)

        pixmap_rect = self.get_pixmap_rect()
        scale_x = pixmap_rect.width() / self.original_size[0]
        scale_y = pixmap_rect.height() / self.original_size[1]

        # Dibujar el bbox original si existe
        if self.bbox:
            pen.setColor(QColor(255, 0, 0))  # Rojo para el bbox original
            painter.setPen(pen)
            x1 = pixmap_rect.x() + int(self.bbox[0] * scale_x)
            x2 = pixmap_rect.x() + int(self.bbox[1] * scale_x)
            y1 = pixmap_rect.y() + int(self.bbox[2] * scale_y)
            y2 = pixmap_rect.y() + int(self.bbox[3] * scale_y)
            painter.drawRect(x1, y1, x2 - x1, y2 - y1)

        # Dibujar el bbox actual si se está dibujando
        if self.current_bbox:
            pen.setColor(QColor(0, 255, 0))  # Verde para el bbox actual
            painter.setPen(pen)
            x1 = pixmap_rect.x() + int(self.current_bbox[0] * scale_x)
            x2 = pixmap_rect.x() + int(self.current_bbox[1] * scale_x)
            y1 = pixmap_rect.y() + int(self.current_bbox[2] * scale_y)
            y2 = pixmap_rect.y() + int(self.current_bbox[3] * scale_y)
            painter.drawRect(x1, y1, x2 - x1, y2 - y1)

    def get_pixmap_rect(self):
        if not self.pixmap():
            return QRect()
        
        scaled_size = self.pixmap().size()
        scaled_size.scale(self.size(), Qt.KeepAspectRatio)
        
        x = (self.width() - scaled_size.width()) // 2
        y = (self.height() - scaled_size.height()) // 2
        
        return QRect(x, y, scaled_size.width(), scaled_size.height())

class ClassificationDialog(QDialog):
    def __init__(self, categorias, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clasificar Bounding Box")
        self.setModal(True)
        
        # Configurar el tamaño mínimo del diálogo
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Label de instrucción
        instruction_label = QLabel("Ingrese la categoría para el bounding box:")
        layout.addWidget(instruction_label)
        
        # Campo de entrada con autocompletado
        self.entrada = AutoCompleteLineEdit(categorias)
        self.entrada.returnPressed.connect(self.accept)
        layout.addWidget(self.entrada)
        
        # Botones
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Aceptar")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
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
        super().accept()

class ClasificadorImagenes(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clasificador de Imágenes")
        self.setWindowIcon(QIcon("icono.png"))
        
        # Obtener la resolución de la pantalla
        screen = QApplication.primaryScreen().geometry()
        window_width = int(screen.width() * 0.8)
        window_height = int(screen.height() * 0.8)
        self.setMinimumSize(window_width, window_height)
        
        # Variables de estado
        self.current_bbox = None
        self.bbox_counter = 0  # Contador para los nombres de las imágenes
        
        # Crear el widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        layout = QVBoxLayout(central_widget)
        
        # Obtener la resolución de la pantalla
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        screen_height = screen_size.height()

        # Ajustar tamaños según la resolución
        # Para 720p (1280x720)
        if screen_height <= 720:
            self.window_width = 1100
            self.window_height = 680
            self.container_width = 500
            self.image_size = (500, 380)
        # Para 1080p (1920x1080)
        elif screen_height <= 1080:
            self.window_width = 1400
            self.window_height = 900
            self.container_width = 650
            self.image_size = (650, 500)
        # Para 2K (2560x1440) o superior
        else:
            self.window_width = 1800
            self.window_height = 1200
            self.container_width = 850
            self.image_size = (850, 650)

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
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 5)

        # Layout horizontal para las imágenes
        images_layout = QHBoxLayout()
        images_layout.setSpacing(20)

        # Contenedor para la imagen original
        left_container = QWidget()
        left_container.setFixedWidth(self.container_width)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Label para la imagen original
        self.label_imagen = ImageLabel(self.image_size)
        left_layout.addWidget(self.label_imagen)
        images_layout.addWidget(left_container)

        # Contenedor para la imagen con zoom
        right_container = QWidget()
        right_container.setFixedWidth(self.container_width)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Label para la imagen con zoom
        self.label_zoom = ImageLabel(self.image_size)
        right_layout.addWidget(self.label_zoom)
        images_layout.addWidget(right_container)

        layout.addLayout(images_layout)

        # Layout horizontal para la entrada
        input_layout = QHBoxLayout()
        input_layout.setSpacing(5)
        
        # Label para la entrada
        input_layout.addWidget(QLabel("Categoría:"))
        
        # Campo de entrada con autocompletado
        self.entrada = AutoCompleteLineEdit(self.categorias)
        self.entrada.returnPressed.connect(self.procesar_clasificacion)
        self.entrada.nextImageSignal.connect(self.siguiente_imagen)
        input_layout.addWidget(self.entrada)
        
        layout.addLayout(input_layout)

        # Layout horizontal para las etiquetas inferiores
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(5)

        # Label para el progreso
        self.label_progreso = QLabel()
        self.label_progreso.setAlignment(Qt.AlignLeft)
        self.label_progreso.setMaximumHeight(20)
        bottom_layout.addWidget(self.label_progreso)

        # Label para el nombre de la imagen
        self.label_nombre_imagen = QLabel()
        self.label_nombre_imagen.setAlignment(Qt.AlignRight)
        self.label_nombre_imagen.setMaximumHeight(20)
        bottom_layout.addWidget(self.label_nombre_imagen)

        layout.addLayout(bottom_layout)

    def mostrar_imagen_actual(self):
        if self.imagen_actual_index >= len(self.imagenes):
            QMessageBox.information(self, "Completado", "¡Has clasificado todas las imágenes!")
            self.close()
            return

        # Limpiar el campo de entrada ANTES de cualquier otra operación
        self.entrada.blockSignals(True)
        self.entrada.clear()
        self.entrada.setText("")  # Forzar texto vacío
        self.entrada.blockSignals(False)

        # Actualizar etiqueta de progreso
        self.label_progreso.setText(
            f"Imagen {self.imagen_actual_index + 1} de {len(self.imagenes)}"
        )

        # Cargar y mostrar imagen
        imagen_nombre = self.imagenes[self.imagen_actual_index]
        imagen_path = os.path.join('photos', imagen_nombre)
        
        # Mostrar el nombre de la imagen
        self.label_nombre_imagen.setText(imagen_nombre)
        imagen = Image.open(imagen_path)
        
        # Guardar tamaño original
        original_size = imagen.size

        # Redimensionar imagen manteniendo proporción
        display_size = self.image_size
        imagen.thumbnail(display_size, Image.LANCZOS)
        
        # Convertir imagen de PIL a QPixmap
        imagen_path_temp = "temp_image.png"
        imagen.save(imagen_path_temp)
        pixmap = QPixmap(imagen_path_temp)
        
        # Mostrar imagen original
        self.label_imagen.setPixmap(pixmap)
        
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
            
            # Limpiar archivos temporales
            os.remove("temp_zoom.png")
        else:
            QMessageBox.warning(self, "Advertencia", f"No se encontró bounding box para la imagen: {imagen_nombre}")
            self.label_imagen.set_bbox(None, None)
            self.label_zoom.setPixmap(QPixmap())  # Limpiar imagen de zoom
        
        os.remove(imagen_path_temp)
        
        # Dar foco al campo de entrada
        self.entrada.setFocus()

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