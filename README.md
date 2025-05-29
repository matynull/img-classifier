# Clasificador de Imágenes

Este script permite clasificar imágenes manualmente mostrándolas una por una y permitiendo al usuario asignarlas a diferentes categorías.

## Requisitos

- Python 3.x
- PyQt5
- Pillow (PIL)

## Instalación

1. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

## Preparación

1. Crear un archivo `categorias.txt` en la misma carpeta del script con las categorías deseadas (una por línea).
2. Colocar las imágenes a clasificar (jpg o png) en la misma carpeta del script.
3. Si se desea usar bounding boxes, crear un archivo `bbox.txt` con el formato:
   ```
   nombre_imagen categoria x1 x2 y1 y2
   ```

## Uso

1. Ejecutar el script:
```bash
python clasificador.py
```

2. Se mostrará una ventana con:
   - La imagen actual en tamaño completo
   - Una vista ampliada del área de interés (si hay bounding box)
   - Un campo de entrada para la categoría
   - Contador de progreso
   - Nombre de la imagen actual

3. Para clasificar imágenes:
   - El campo de entrada mostrará automáticamente la última categoría utilizada
   - Puedes escribir una nueva categoría o usar la que se muestra
   - Presiona Enter para clasificar la imagen
   - La imagen se moverá automáticamente a una carpeta con el nombre de la categoría

4. Funciones especiales:
   - Autocompletado de categorías mientras escribes
   - Control + tecla para saltar la imagen actual (se moverá a la carpeta "skip")
   - La información de bounding box se preservará en un archivo bbox.txt dentro de cada carpeta de categoría

5. El proceso continúa hasta clasificar todas las imágenes.

## Notas

- Las imágenes deben estar en formato JPG o PNG
- Se crearán automáticamente las carpetas para cada categoría
- Las imágenes se moverán (no se copiarán) a sus respectivas carpetas
- Si una imagen tiene bounding box, se mostrará un recuadro rojo en la imagen y una vista ampliada
- Las categorías deben coincidir exactamente con las listadas en categorias.txt 