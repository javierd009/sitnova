# 🤖 Modelos de YOLO para SITNOVA

Esta carpeta contiene los modelos de YOLO para detección de vehículos y OCR.

## Modelos Necesarios

### 1. YOLOv8 Base (Detección de vehículos y personas)

```bash
# Descargar modelo base nano (más rápido)
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt

# O modelo small (más preciso)
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt
```

### 2. YOLOv8 para Placas (Fine-tuned)

Opciones:

#### Opción A: Entrenar tu propio modelo

```python
from ultralytics import YOLO

# Cargar modelo pre-entrenado
model = YOLO('yolov8n.pt')

# Entrenar con dataset de placas
model.train(
    data='plates_dataset.yaml',
    epochs=100,
    imgsz=640,
    batch=16
)

# Guardar
model.save('yolov8_plates.pt')
```

#### Opción B: Usar modelo público

Buscar en:
- Roboflow Universe: https://universe.roboflow.com/
- Hugging Face: https://huggingface.co/models?search=license-plate

### 3. Configuración en .env

```env
YOLO_MODEL_PATH=models/yolov8n.pt
YOLO_PLATE_MODEL=models/yolov8_plates.pt
YOLO_PERSON_MODEL=models/yolov8n.pt
```

## Estructura de Archivos

```
models/
├── README.md                 # Este archivo
├── yolov8n.pt               # Modelo base nano (23MB)
├── yolov8s.pt               # Modelo base small (44MB) - opcional
├── yolov8_plates.pt         # Modelo fine-tuned para placas
└── plates_dataset/          # Dataset de entrenamiento (opcional)
    ├── train/
    ├── val/
    └── data.yaml
```

## Alternativas Ligeras

Si necesitas ejecutar en dispositivos con recursos limitados:

### YOLOv8n (Nano) - Recomendado
- **Tamaño**: ~23MB
- **Velocidad**: ~100 FPS en GPU, ~10 FPS en CPU
- **Precisión**: mAP ~37.3%

### YOLOv8s (Small)
- **Tamaño**: ~44MB
- **Velocidad**: ~80 FPS en GPU, ~5 FPS en CPU
- **Precisión**: mAP ~44.9%

### YOLOv8m (Medium)
- **Tamaño**: ~99MB
- **Velocidad**: ~50 FPS en GPU, ~2 FPS en CPU
- **Precisión**: mAP ~50.2%

## Optimización para Producción

### 1. Exportar a ONNX (más rápido en CPU)

```python
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
model.export(format='onnx')
# Genera: yolov8n.onnx
```

### 2. Exportar a TensorRT (más rápido en GPU NVIDIA)

```python
model.export(format='engine')  # Requiere TensorRT
```

### 3. Exportar a CoreML (para macOS/iOS)

```python
model.export(format='coreml')
```

## Notas

- Los archivos `.pt` **NO** deben subirse a git (están en .gitignore)
- Descargar modelos al hacer deploy
- Para producción, considerar usar modelos optimizados (ONNX, TensorRT)
- Las placas costarricenses tienen formato `ABC-123` (3 letras, guion, 3 números)

## Recursos

- **Ultralytics Docs**: https://docs.ultralytics.com/
- **YOLO Models**: https://github.com/ultralytics/ultralytics
- **License Plate Datasets**:
  - https://universe.roboflow.com/search?q=license%20plate
  - https://www.kaggle.com/datasets/andrewmvd/car-plate-detection
