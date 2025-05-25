# Clasificador de Imágenes

Este script permite clasificar imágenes manualmente mostrándolas una por una y permitiendo al usuario asignarlas a diferentes categorías.

## Requisitos

- Python 3.x
- Pillow (PIL)
- tkinter (viene incluido con Python normalmente)

## Instalación

1. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

## Preparación

1. Crear un archivo `categorias.txt` en la misma carpeta del script con las categorías deseadas (una por línea).
2. Colocar las imágenes a clasificar (jpg o png) en la misma carpeta del script.

## Uso

1. Ejecutar el script:
```bash
python clasificador.py
```

2. Se mostrará una ventana con:
   - La imagen actual
   - Botones para cada categoría
   - Contador de progreso

3. Al hacer clic en una categoría:
   - Se creará una carpeta con el nombre de la categoría (si no existe)
   - La imagen se moverá a esa carpeta
   - Se mostrará la siguiente imagen

4. El proceso continúa hasta clasificar todas las imágenes.

## Notas

- Las imágenes deben estar en formato JPG o PNG
- Se crearán automáticamente las carpetas para cada categoría
- Las imágenes se moverán (no se copiarán) a sus respectivas carpetas 