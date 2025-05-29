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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bbox = None
        self.original_size = None
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(QSize(400, 300))  # Set minimum size for better layout

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

        # Layout horizontal para las imágenes
        images_layout = QHBoxLayout()

        # Label para la imagen original
        self.label_imagen = ImageLabel()
        images_layout.addWidget(self.label_imagen)

        # Label para la imagen con zoom
        self.label_zoom = ImageLabel()
        images_layout.addWidget(self.label_zoom)

        layout.addLayout(images_layout)

        # Layout horizontal para la entrada
        input_layout = QHBoxLayout()
        
        # Label para la entrada
        input_layout.addWidget(QLabel("Categoría:"))
        
        # Campo de entrada con autocompletado
        self.entrada = AutoCompleteLineEdit(self.categorias)
        self.entrada.returnPressed.connect(self.procesar_clasificacion)
        self.entrada.nextImageSignal.connect(self.siguiente_imagen)
        input_layout.addWidget(self.entrada)
        
        layout.addLayout(input_layout)

        # Label para el progreso
        self.label_progreso = QLabel()
        self.label_progreso.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label_progreso)

        # Label para el nombre de la imagen
        self.label_nombre_imagen = QLabel()
        self.label_nombre_imagen.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label_nombre_imagen)

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
        imagen_path = self.imagenes[self.imagen_actual_index]
        # Mostrar el nombre de la imagen
        self.label_nombre_imagen.setText(imagen_path)
        imagen = Image.open(imagen_path)
        
        # Guardar tamaño original
        original_size = imagen.size

        # Redimensionar imagen manteniendo proporción
        display_size = (400, 300)  # Tamaño reducido para acomodar ambas imágenes
        imagen.thumbnail(display_size, Image.LANCZOS)
        
        # Convertir imagen de PIL a QPixmap
        imagen_path_temp = "temp_image.png"
        imagen.save(imagen_path_temp)
        pixmap = QPixmap(imagen_path_temp)
        
        # Mostrar imagen original
        self.label_imagen.setPixmap(pixmap)
        
        # Establecer bounding box si existe
        if imagen_path in self.bboxes:
            bbox = self.bboxes[imagen_path]
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
            
            imagen_recortada = imagen_original.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            imagen_recortada.thumbnail(display_size, Image.LANCZOS)
            
            # Guardar y mostrar imagen recortada
            imagen_recortada.save("temp_zoom.png")
            pixmap_zoom = QPixmap("temp_zoom.png")
            self.label_zoom.setPixmap(pixmap_zoom)
            
            # Limpiar archivos temporales
            os.remove("temp_zoom.png")
        else:
            QMessageBox.warning(self, "Advertencia", f"No se encontró bounding box para la imagen: {imagen_path}")
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

        # Guardar la última categoría usada antes de cualquier operación
        self.entrada.last_category = categoria

        # Mover imagen
        try:
            # Obtener bbox de la imagen antes de moverla
            bbox_info = None
            if imagen_actual in self.bboxes:
                bbox_info = self.bboxes[imagen_actual]

            # Mover la imagen
            shutil.move(imagen_actual, os.path.join(categoria, imagen_actual))
            
            # Si hay información de bbox, guardarla en el archivo bbox de la categoría
            if bbox_info:
                bbox_path = os.path.join(categoria, 'bbox.txt')
                with open(bbox_path, 'a', encoding='utf-8') as f:
                    # Escribir en el mismo formato que el archivo bbox original
                    x1, x2, y1, y2 = bbox_info
                    f.write(f"{imagen_actual} {categoria} {x1} {x2} {y1} {y2}\n")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al mover la imagen: {str(e)}")
            return

        # Asegurarse de que el input esté vacío antes de pasar a la siguiente imagen
        self.entrada.blockSignals(True)  # Bloquear señales temporalmente
        self.entrada.clear()  # Limpiar el texto
        self.entrada.blockSignals(False)  # Restaurar señales

        self.imagen_actual_index += 1
        self.mostrar_imagen_actual()

def main():
    app = QApplication(sys.argv)
    window = ClasificadorImagenes()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 