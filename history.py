import streamlit as st
import pandas as pd
from database import get_user_history, delete_detection_by_id, delete_all_user_history, delete_multiple_detections
from datetime import datetime
import os
from PIL import Image
import json

def format_timestamp(timestamp_str):
    try:
        for fmt in ['%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y']:
            try:
                dt = datetime.strptime(timestamp_str, fmt)
                return dt.strftime('%d/%m/%Y')
            except:
                continue
        return timestamp_str
    except:
        return timestamp_str

def get_status_emoji(prediction):
    return {'healthy': '🌿', 'curly': '🍃', 'yellow': '🟡'}.get(prediction.lower(), '❓')

def get_treatment_recommendation(condition):
    treatments = {
        'healthy': 'Pertahankan pola perawatan rutin seperti penyiraman cukup, pemupukan seimbang, dan pengendalian hama secara berkala.',
        'curly': 'Semprot tanaman secara rutin dengan pestisida nabati yang aman bagi lingkungan untuk mengendalikan kutu kebul sebagai penyebar virus.',
        'yellow': 'Semprot tanaman secara rutin dengan pestisida nabati yang aman bagi lingkungan untuk mengendalikan kutu kebul sebagai penyebar virus.'
    }
    return treatments.get(condition.lower(), "Tidak ada rekomendasi khusus")

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
            "Tidak ditemukan gejala penyakit pada daun cabai. "
        ),
        'curly': (
            "Penyakit ini sering disebabkan oleh serangan kutu kebul yang membawa virus kuning atau oleh faktor lingkungan seperti kekurangan unsur hara. Serangan virus ini ditandai dengan daun menggulung/keriting, pertumbuhan tanaman terhambat.\n\n"
        ),
        'yellow': (
            "Tanaman cabai kemungkinan terserang virus Gemini, yang ditularkan oleh serangga kutu kebul (Bemisia tabaci). Serangan virus ini biasanya ditandai dengan daun menguning, tepi daun mengerut, dan tanaman menjadi kerdil serta tidak berbuah.\n\n"
        )
    }
    return penjelasan.get(condition.lower(), "Tidak ada detail penyakit.")

def show_history(username):
    st.markdown("<h1 style='color:#1B5E20;'>📋 Riwayat Deteksi</h1>", unsafe_allow_html=True)
    
    history_data = get_user_history(username)
    
    if not history_data:
        st.info("Belum ada riwayat deteksi.")
        return
    
    total_entries = len(history_data)
    healthy_count = curly_count = yellow_count = 0
    
    for item in history_data:
        _, _, _, _, _, _, detection_details_json = item
        if detection_details_json:
            try:
                detection_details = json.loads(detection_details_json)
                detection_counts = detection_details.get('detection_counts', {})
                if 'healthy' in detection_counts:
                    healthy_count += 1
                if 'curly' in detection_counts:
                    curly_count += 1
                if 'yellow' in detection_counts:
                    yellow_count += 1
            except:
                prediction = item[2].lower()
                if prediction == 'healthy':
                    healthy_count += 1
                elif prediction == 'curly':
                    curly_count += 1
                elif prediction == 'yellow':
                    yellow_count += 1
        else:
            prediction = item[2].lower()
            if prediction == 'healthy':
                healthy_count += 1
            elif prediction == 'curly':
                curly_count += 1
            elif prediction == 'yellow':
                yellow_count += 1
    
    avg_confidence = sum(item[3] for item in history_data) / total_entries
    
    st.markdown("""
        <style>
        .metric-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            padding: 10px;
            border-radius: 5px;
            background-color: #f9f9f9;
        }
        .metric-value {
            font-size: 28px;
            font-weight: bold;
        }
        .metric-label {
            font-size: 16px;
            margin-bottom: 5px;
        }
        </style>
        """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Semua</div>
                <div class="metric-value">{total_entries}</div>
            </div>
            """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Healthy</div>
                <div class="metric-value">{healthy_count}</div>
            </div>
            """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Curly</div>
                <div class="metric-value">{curly_count}</div>
            </div>
            """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Yellow</div>
                <div class="metric-value">{yellow_count}</div>
            </div>
            """, unsafe_allow_html=True)

    st.metric("Confidence Rata-rata", f"{(avg_confidence*100):.2f}%")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Hapus Semua"):
            st.session_state.show_delete_confirm = True
    with col2:
        if st.button("Pilih Multiple"):
            st.session_state.multi_select = not st.session_state.get('multi_select', False)
    
    if st.session_state.get('show_delete_confirm', False):
        st.warning("Hapus semua riwayat?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Ya"):
                deleted = delete_all_user_history(username)
                st.success(f"🗑️ Berhasil menghapus {deleted} riwayat")
                st.session_state.show_delete_confirm = False
                st.rerun()
        with col2:
            if st.button("Batal"):
                st.session_state.show_delete_confirm = False
                st.rerun()
    
    if st.session_state.get('multi_select', False):
        st.info("Mode pilih multiple aktif")
        selected_items = []
        if st.checkbox("🔘 Pilih Semua"):
            selected_items = [item[0] for item in history_data]
        else:
            for item in history_data:
                detection_id, image_name, prediction, confidence, timestamp, _, detection_details_json = item
                conditions_str = prediction.title()
                if detection_details_json:
                    try:
                        detection_details = json.loads(detection_details_json)
                        detection_counts = detection_details.get('detection_counts', {})
                        if detection_counts:
                            detected_conditions = list(detection_counts.keys())
                            conditions_str = " dan ".join([cond.title() for cond in detected_conditions])
                    except:
                        pass
                formatted_time = format_timestamp(timestamp)
                if st.checkbox(f"{image_name} - {conditions_str} - {formatted_time}", key=f"multi_{detection_id}"):
                    selected_items.append(detection_id)
        if selected_items:
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Hapus {len(selected_items)} Item"):
                    deleted = delete_multiple_detections(selected_items, username)
                    st.success(f"Berhasil menghapus {deleted} item")
                    st.session_state.multi_select = False
                    st.rerun()
            with col2:
                if st.button("Batal"):
                    st.session_state.multi_select = False
                    st.rerun()
    
    col1, col2 = st.columns(2)
    filter_condition = col1.selectbox("Filter kondisi", ["All", "Healthy", "Curly", "Yellow"])
    sort_option = col2.selectbox("Urutkan", ["Terbaru", "Terlama", "Confidence Tinggi"])
    
    filtered_data = history_data
    if filter_condition != "Semua":
        filter_map = {"Sehat": "healthy", "Keriting": "curly", "Menguning": "yellow"}
        filtered_condition = filter_map[filter_condition]
        filtered_data = []
        for item in history_data:
            _, _, prediction, _, _, _, detection_details_json = item
            include_item = False
            if detection_details_json:
                try:
                    detection_details = json.loads(detection_details_json)
                    detection_counts = detection_details.get('detection_counts', {})
                    if filtered_condition in detection_counts:
                        include_item = True
                except:
                    if prediction.lower() == filtered_condition:
                        include_item = True
            else:
                if prediction.lower() == filtered_condition:
                    include_item = True
            if include_item:
                filtered_data.append(item)
    if sort_option == "Terlama":
        filtered_data = list(reversed(filtered_data))
    elif sort_option == "Confidence Tinggi":
        filtered_data = sorted(filtered_data, key=lambda x: x[3], reverse=True)
    
    st.markdown("### 📝 Detail Riwayat")
    for item in filtered_data:
        detection_id, image_name, prediction, confidence, timestamp, image_path, detection_details_json = item
        formatted_time = format_timestamp(timestamp)
        detection_details = None
        if detection_details_json:
            try:
                detection_details = json.loads(detection_details_json)
            except:
                pass
        detection_counts = {}
        all_detections = []
        num_detections = 1
        if detection_details:
            detection_counts = detection_details.get('detection_counts', {})
            all_detections = detection_details.get('all_detections', [])
            num_detections = detection_details.get('num_detections', 1)
            if not all_detections and detection_counts:
                for class_name, count in detection_counts.items():
                    for i in range(count):
                        all_detections.append({'class': class_name, 'confidence': confidence})
        else:
            detection_counts = {prediction.lower(): 1}
            all_detections = [{'class': prediction.lower(), 'confidence': confidence}]
        detected_conditions = list(detection_counts.keys())
        conditions_str = " dan ".join([cond.title() for cond in detected_conditions])
        expander_title = f"{image_name} - {conditions_str} - {formatted_time}"
        with st.expander(expander_title):
            cols = st.columns([1, 1])
            with cols[0]:
                if image_path and os.path.exists(image_path):
                    try:
                        detection_image = Image.open(image_path)
                        st.image(detection_image, use_container_width=True, caption=f"Hasil Deteksi")
                    except Exception as e:
                        st.error(f"Tidak dapat menampilkan gambar: {str(e)}")
                else:
                    st.info("Gambar hasil deteksi tidak tersedia untuk riwayat ini.")
            with cols[1]:
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
                    emoji = get_status_emoji(condition)
                    treatment = get_treatment_recommendation(condition)
                    st.write(f" **{condition.title()}:** {treatment}")
                st.write("**Detail semua deteksi:**")
                class_detections = {}
                for detection in all_detections:
                    class_name = detection['class']
                    if class_name not in class_detections:
                        class_detections[class_name] = []
                    class_detections[class_name].append(detection['confidence'])
                for condition, confidences in class_detections.items():
                    emoji_detail = get_status_emoji(condition)
                    count = len(confidences)
                    st.write(f"* {emoji_detail} {condition.title()}: {count} deteksi")
                    for idx, conf in enumerate(confidences, 1):
                        st.write(f"  • Deteksi #{idx}: {conf*100:.2f}%")
            st.progress(confidence)
            st.success(f"Tersimpan: {formatted_time}")
            if st.button("Hapus", key=f"del_{detection_id}"):
                if delete_detection_by_id(detection_id, username):
                    st.success("Dihapus")
                    st.rerun()