import os
import sys
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QCompleter, QMessageBox)
from PyQt5.QtCore import Qt, QSize, QRect, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
from PIL import Image
from pathlib import Path

class AutoCompleteLineEdit(QLineEdit):
    nextImageSignal = pyqtSignal()  # Nueva señal para siguiente imagen
    
    def __init__(self, completevalues, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._completer = None
        self._suggestion = ""
        self.last_category = ""  # Para almacenar la última categoría
        self.textChanged.connect(self.updateSuggestion)
        self.setCompleter(completevalues)

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
                # Se busca la primera coincidencia que empiece con el texto (sin distinguir mayúsculas)
                for row in range(model.rowCount()):
                    idx = model.index(row, 0)
                    candidate = model.data(idx)
                    if candidate.lower().startswith(text.lower()):
                        self._suggestion = candidate
                        break
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab:
            if self.last_category:  # Si hay una categoría anterior, usarla
                self.setText(self.last_category)
                self.setCursorPosition(len(self.last_category))
                event.accept()
                return
            # Si no hay categoría anterior, usar la sugerencia como antes
            current_text = self.text()
            if self._suggestion and len(self._suggestion) > len(current_text):
                self.setText(self._suggestion)
                self.setCursorPosition(len(self._suggestion))
                event.accept()
                return
        elif event.key() == Qt.Key_Control:
            self.nextImageSignal.emit()  # Emitir señal para siguiente imagen
            event.accept()
            return
        super().keyPressEvent(event)

    def focusNextPrevChild(self, next):
        return False

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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bbox = None
        self.original_size = None
        self.setAlignment(Qt.AlignCenter)

    def set_bbox(self, bbox, original_size):
        self.bbox = bbox
        self.original_size = original_size
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.bbox and self.pixmap() and self.original_size:
            painter = QPainter(self)
            pen = QPen(QColor(255, 0, 0))  # Color rojo
            pen.setWidth(1)  # Grosor fino
            painter.setPen(pen)
            
            # Obtener el rectángulo donde se dibuja la imagen
            pixmap_rect = self.get_pixmap_rect()
            
            # Calcular las escalas
            scale_x = pixmap_rect.width() / self.original_size[0]
            scale_y = pixmap_rect.height() / self.original_size[1]
            
            # Aplicar la escala a las coordenadas del bbox
            x1 = pixmap_rect.x() + int(self.bbox[0] * scale_x)
            x2 = pixmap_rect.x() + int(self.bbox[1] * scale_x)
            y1 = pixmap_rect.y() + int(self.bbox[2] * scale_y)
            y2 = pixmap_rect.y() + int(self.bbox[3] * scale_y)
            
            painter.drawRect(x1, y1, x2 - x1, y2 - y1)

    def get_pixmap_rect(self):
        if not self.pixmap():
            return QRect()
        
        # Obtener el tamaño escalado del pixmap
        scaled_size = self.pixmap().size()
        scaled_size.scale(self.size(), Qt.KeepAspectRatio)
        
        # Calcular las coordenadas para centrar el pixmap
        x = (self.width() - scaled_size.width()) // 2
        y = (self.height() - scaled_size.height()) // 2
        
        return QRect(x, y, scaled_size.width(), scaled_size.height())

class ClasificadorImagenes(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clasificador de Imágenes")
        self.setGeometry(100, 100, 800, 600)

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
        extensiones = ('.jpg', '.jpeg', '.png')
        return [f for f in os.listdir('.') if f.lower().endswith(extensiones)]

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

        # Label para la imagen
        self.label_imagen = ImageLabel()
        layout.addWidget(self.label_imagen)

        # Layout horizontal para la entrada
        input_layout = QHBoxLayout()
        
        # Label para la entrada
        input_layout.addWidget(QLabel("Categoría:"))
        
        # Campo de entrada con autocompletado
        self.entrada = AutoCompleteLineEdit(self.categorias)
        self.entrada.returnPressed.connect(self.procesar_clasificacion)
        self.entrada.nextImageSignal.connect(self.siguiente_imagen)  # Conectar la señal
        input_layout.addWidget(self.entrada)
        
        layout.addLayout(input_layout)

        # Label para el progreso
        self.label_progreso = QLabel()
        self.label_progreso.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label_progreso)

    def mostrar_imagen_actual(self):
        if self.imagen_actual_index >= len(self.imagenes):
            QMessageBox.information(self, "Completado", "¡Has clasificado todas las imágenes!")
            self.close()
            return

        # Actualizar etiqueta de progreso
        self.label_progreso.setText(
            f"Imagen {self.imagen_actual_index + 1} de {len(self.imagenes)}"
        )

        # Cargar y mostrar imagen
        imagen_path = self.imagenes[self.imagen_actual_index]
        imagen = Image.open(imagen_path)
        
        # Guardar tamaño original
        original_size = imagen.size

        # Redimensionar imagen manteniendo proporción
        display_size = (700, 400)
        imagen.thumbnail(display_size, Image.LANCZOS)
        
        # Convertir imagen de PIL a QPixmap
        imagen_path_temp = "temp_image.png"
        imagen.save(imagen_path_temp)
        pixmap = QPixmap(imagen_path_temp)
        os.remove(imagen_path_temp)
        
        # Mostrar imagen
        self.label_imagen.setPixmap(pixmap)
        
        # Establecer bounding box si existe
        if imagen_path in self.bboxes:
            self.label_imagen.set_bbox(self.bboxes[imagen_path], original_size)
        else:
            QMessageBox.warning(self, "Advertencia", f"No se encontró bounding box para la imagen: {imagen_path}")
            self.label_imagen.set_bbox(None, None)
        
        # Limpiar y dar foco a la entrada
        self.entrada.clear()
        self.entrada.setFocus()

    def procesar_clasificacion(self):
        categoria = self.entrada.text().strip()
        if not categoria:
            return

        if categoria not in self.categorias:
            QMessageBox.warning(self, "Error", "Categoría no válida")
            return

        self.clasificar_imagen(categoria)

    def siguiente_imagen(self):
        """Mueve la imagen actual a la carpeta skip y avanza a la siguiente"""
        if self.imagen_actual_index >= len(self.imagenes):
            return

        imagen_actual = self.imagenes[self.imagen_actual_index]
        
        # Crear directorio skip si no existe
        skip_dir = "skip"
        Path(skip_dir).mkdir(exist_ok=True)

        # Mover imagen a la carpeta skip
        try:
            shutil.move(imagen_actual, os.path.join(skip_dir, imagen_actual))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al mover la imagen a skip: {str(e)}")
            return

        self.imagen_actual_index += 1
        self.mostrar_imagen_actual()

    def clasificar_imagen(self, categoria):
        if self.imagen_actual_index >= len(self.imagenes):
            return

        imagen_actual = self.imagenes[self.imagen_actual_index]

        # Crear directorio si no existe
        Path(categoria).mkdir(exist_ok=True)

        # Mover imagen
        try:
            shutil.move(imagen_actual, os.path.join(categoria, imagen_actual))
            # Guardar la última categoría usada
            self.entrada.last_category = categoria
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al mover la imagen: {str(e)}")
            return

        self.imagen_actual_index += 1
        self.mostrar_imagen_actual()

def main():
    app = QApplication(sys.argv)
    window = ClasificadorImagenes()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 