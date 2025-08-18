import streamlit as st
from PIL import Image
import numpy as np
from ultralytics import YOLO
import cv2
from datetime import datetime
from database import save_detection_result

st.markdown("""
    <style>
    section[data-testid="stFileUploader"] button {
        color: white !important;
        background-color: #1B5E20 !important;
        border: 2px solid #1B5E20 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 18px !important;
        transition: 0.3s;
    }
    section[data-testid="stFileUploader"] button:hover {
        background-color: #388E3C !important;
        border-color: #388E3C !important;
        color: #fff !important;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_model():
    try:
        return YOLO('best.pt')
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def draw_bounding_boxes(image, results):
    img_array = np.array(image)
    img_cv2 = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    model = load_model()
    class_names = model.names if model else {0: 'curly', 1: 'healthy', 2: 'yellow'}
    
    colors = {
        'healthy': (0, 255, 0),      
        'curly': (0, 165, 255),       
        'yellow': (0, 255, 255),     
        'Healthy': (0, 255, 0),
        'Curly': (0, 165, 255), 
        'Yellow': (0, 255, 255)
    }
    
    font_scale = 1.5      
    thickness = 8         
    text_thickness = 3    
    
    detection_details = []
    
    if len(results) > 0 and hasattr(results[0], 'boxes') and results[0].boxes is not None:
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            class_id = int(box.cls[0].cpu().numpy())
            confidence = float(box.conf[0].cpu().numpy())
            class_name = class_names.get(class_id, f'class_{class_id}')
            color = colors.get(class_name, (128, 128, 128))
            
            detection_details.append({
                'class': class_name.lower(),
                'confidence': confidence
            })
            
            cv2.rectangle(img_cv2, (x1, y1), (x2, y2), color, thickness)
            
            label = f"{class_name}: {confidence*100:.2f}%"
            
            (text_width, text_height), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_thickness)
            label_y = y1 - 10 if y1 - 40 > 0 else y2 + 40
            cv2.rectangle(img_cv2, (x1, label_y - text_height - 20), (x1 + text_width + 20, label_y + 5), (0, 0, 0), -1)
            cv2.putText(img_cv2, label, (x1 + 10, label_y - 10), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), text_thickness)
    
    return Image.fromarray(cv2.cvtColor(img_cv2, cv2.COLOR_BGR2RGB)), detection_details

def process_results(results):
    if not results or len(results) == 0:
        return "healthy", 0.5, {}, []
    result = results[0]
    model = load_model()
    class_names = model.names if model else {0: 'curly', 1: 'healthy', 2: 'yellow'}
    all_detections = []
    detection_counts = {}
    if hasattr(result, 'boxes') and result.boxes is not None and len(result.boxes) > 0:
        highest_confidence = 0
        main_prediction = "healthy"
        for box in result.boxes:
            class_id = int(box.cls[0].cpu().numpy())
            confidence = float(box.conf[0].cpu().numpy())
            class_name = class_names.get(class_id, f'class_{class_id}').lower()
            all_detections.append({'class': class_name, 'confidence': confidence})
            detection_counts[class_name] = detection_counts.get(class_name, 0) + 1
            if confidence > highest_confidence:
                highest_confidence = confidence
                main_prediction = class_name
        return main_prediction, highest_confidence, detection_counts, all_detections
    return "healthy", 0.5, {"healthy": 1}, []

def get_treatment_recommendation(condition):
    treatments = {
        'healthy': 'Pertahankan pola perawatan rutin seperti penyiraman cukup, pemupukan seimbang, dan pengendalian hama secara berkala.',
        'curly': 'Semprot tanaman secara rutin dengan pestisida nabati yang aman bagi lingkungan untuk mengendalikan kutu kebul sebagai penyebar virus.',
        'yellow': 'Semprot tanaman secara rutin dengan pestisida nabati yang aman bagi lingkungan untuk mengendalikan kutu kebul sebagai penyebar virus.'
    }
    return treatments.get(condition.lower(), "Tidak ada rekomendasi khusus.")

def get_status_emoji(prediction):
    return {'healthy': '🌿', 'curly': '🍃', 'yellow': '🟡'}.get(prediction.lower(), '❓')

def get_box_style(condition):
    if condition.lower() == 'healthy':
        return "success"
    elif condition.lower() == 'curly':
        return "warning"
    else:  
        return "error"

def get_disease_detail(condition):
    penjelasan = {
        'healthy': (
            "Tidak ditemukan gejala penyakit pada daun cabai."
        ),
        'curly': (
            "Penyakit ini sering disebabkan oleh serangan kutu kebul yang membawa virus kuning atau oleh faktor lingkungan seperti kekurangan unsur hara. Serangan virus ini ditandai dengan daun menggulung/keriting, pertumbuhan tanaman terhambat."
        ),
        'yellow': (
            "Tanaman cabai kemungkinan terserang virus Gemini, yang ditularkan oleh serangga kutu kebul (Bemisia tabaci). Serangan virus ini biasanya ditandai dengan daun menguning, tepi daun mengerut, dan tanaman menjadi kerdil serta tidak berbuah."
        )
    }
    return penjelasan.get(condition.lower(), "Tidak ada detail penyakit.")

def show_results(detection_counts, main_prediction, confidence, all_detections):
    for condition, count in detection_counts.items():
        emoji = get_status_emoji(condition)
        box_style = get_box_style(condition)
        disease_detail = get_disease_detail(condition)
        if box_style == "success":
            st.success(f"{emoji} Hasil: {condition.title()} ({count} deteksi)\n\n{disease_detail}")
        elif box_style == "warning":
            st.warning(f"{emoji} Hasil: {condition.title()} ({count} deteksi)\n\n{disease_detail}")
        else:
            st.error(f"{emoji} Hasil: {condition.title()} ({count} deteksi)\n\n{disease_detail}")
    st.write("**Penanganan:**")
    for condition in detection_counts.keys():
        treatment = get_treatment_recommendation(condition)
        st.write(f" **{condition.title()}:** {treatment}")
    st.write("**Detail semua deteksi:**")
    class_detections = {}
    for detection in all_detections:
        if detection['class'] not in class_detections:
            class_detections[detection['class']] = []
        class_detections[detection['class']].append(detection['confidence'])
    for condition, confidences in class_detections.items():
        emoji_detail = get_status_emoji(condition)
        count = len(confidences)
        st.write(f"* {emoji_detail} {condition.title()}: {count} deteksi")
        for idx, conf in enumerate(confidences, 1):
            st.write(f"Deteksi #{idx}: {conf*100:.2f}%")

def detect_disease():
    st.markdown("<h1 style='color:#1B5E20;'>🔍 Chili Leaf Disease Detection</h1>", unsafe_allow_html=True)
    st.write("Upload foto daun cabai untuk dianalisis!")
    model = load_model()
    if not model:
        return
    uploaded_file = st.file_uploader("Pilih gambar daun cabai", type=['jpg', 'jpeg', 'png'])
    if uploaded_file:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Gambar Original")
            original_image = Image.open(uploaded_file)
            st.image(original_image, use_container_width=True)
        with col2:
            st.subheader("Hasil Analisis")
            if st.button("Analisis", use_container_width=True):
                detection_time = datetime.now()
                st.info(f"Waktu: {detection_time.strftime('%d/%m/%Y')}")
                with st.spinner("Menganalisis..."):
                    try:
                        results = model(original_image, verbose=False)
                        main_prediction, highest_confidence, detection_counts, all_detections = process_results(results)
                        num_detections = 0
                        result_image = None
                        if hasattr(results[0], 'boxes') and results[0].boxes is not None:
                            num_detections = len(results[0].boxes)
                            if num_detections > 0:
                                result_image, detection_details = draw_bounding_boxes(original_image, results)
                                st.image(result_image, use_container_width=True, caption=f"Hasil Deteksi ({num_detections} daun)")
                        detailed_results = {
                            'main_prediction': main_prediction,
                            'detection_counts': detection_counts,
                            'all_detections': [{'class': d['class'], 'confidence': float(d['confidence'])} for d in all_detections],
                            'num_detections': num_detections
                        }
                        save_detection_result(
                            st.session_state.username, 
                            uploaded_file.name, 
                            main_prediction, 
                            highest_confidence, 
                            detection_time,
                            result_image,  
                            detailed_results  
                        )
                        st.progress(highest_confidence)
                        show_results(detection_counts, main_prediction, highest_confidence, all_detections)
                        st.success(f"Tersimpan: {detection_time.strftime('%d/%m/%Y')}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    else:
        st.info("👆 Upload foto untuk memulai analisis")
        with st.expander("💡 Tips"):
            st.write("""
            - Foto ditempat yang jelas dan terang
            - Hindari bayangan berlebihan
            - Jarak tidak terlalu jauh dari daun
            """)
