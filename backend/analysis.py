import cv2
import numpy as np
try:
    from skimage.metrics import structural_similarity as ssim
except ImportError:
    ssim = None
import tensorflow as tf

# Load Model Once at Startup
MODEL_PATH = "mouth_tumor_vgg16.h5"
try:
    model = tf.keras.models.load_model(MODEL_PATH)
except:
    model = None

def decode_image(img_bytes):
    nparr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

def calculate_ssim(img1_bytes, img2_bytes):
    if ssim is None: return {"error": "SSIM library missing"}
    
    img1 = decode_image(img1_bytes)
    img2 = decode_image(img2_bytes)
    
    # Resize Logic
    h, w = img1.shape[:2]
    img2 = cv2.resize(img2, (w, h))
    
    # Grayscale & Hist Eq
    g1 = cv2.equalizeHist(cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY))
    g2 = cv2.equalizeHist(cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY))
    
    score = ssim(g1, g2)
    return {"ssim_score": float(score)}

def predict_dl(img_bytes):
    if model is None: return {"prediction": "Model Missing", "confidence": 0.0}
    
    img = decode_image(img_bytes)
    img_resized = cv2.resize(img, (224, 224))
    img_arr = np.array(img_resized) / 255.0
    img_arr = np.expand_dims(img_arr, axis=0)
    
    pred = model.predict(img_arr)[0][0]
    label = "Malignant" if pred > 0.5 else "Benign"
    conf = float(pred * 100 if pred > 0.5 else (1 - pred) * 100)
    
    return {"label": label, "confidence": conf}