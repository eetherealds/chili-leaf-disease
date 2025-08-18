import streamlit as st

st.set_page_config(
    page_title="Chili Leaf Disease Detection", 
    page_icon="🌶️", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

from database import init_database, authenticate_user, register_user
from detection import detect_disease
from history import show_history

st.markdown("""
    <style>
    /* BUTTON */
    .stButton>button {
        background-color: #1B5E20 !important;
        color: white !important;
    }
    .stButton>button:hover {
        background-color: #388E3C !important;
        color: #fff !important;
    }
    /* TABS */
    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #1B5E20 !important;
        font-weight: bold;
    }
    div[data-testid="stTabs"] button {
        color: #388E3C !important;
    }
    div[data-testid="stTabs"] div[role="tablist"] > button[aria-selected="true"]::after {
        background-color: #1B5E20 !important;
        height: 3px;
    }
    div[data-testid="stTabs"] div[role="tablist"] > button[aria-selected="true"] {
        border-bottom: none !important;
    }
    /* GREEN TEXT */
    .green-text { color: #1B5E20 !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

def main():
    init_database()
    st.session_state.setdefault('logged_in', False)
    st.session_state.setdefault('username', "")
    if not st.session_state.logged_in:
        show_login_page()
    else:
        show_main_app()

def show_login_page():
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="color: #1B5E20; font-size: 3em;">🌶️ Chili Leaf Detection</h1>
        <p style="font-size: 1.2em; color: #666; max-width: 600px; margin: 0 auto;">
            Membantu petani mengenali gejala penyakit daun cabai lebih awal dengan teknologi citra dan kecerdasan buatan untuk meningkatkan kualitas hasil panen.
        </p>
    </div>
    """, unsafe_allow_html=True)
    with st.columns([1,2,1])[1]:
        tab1, tab2 = st.tabs(["Masuk", "Daftar"])
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Nama Pengguna")
                password = st.text_input("Kata Sandi", type="password")
                if st.form_submit_button("Masuk", use_container_width=True):
                    if username and password and authenticate_user(username, password):
                        st.session_state.logged_in, st.session_state.username = True, username
                        st.rerun()
                    else:
                        st.error("Nama pengguna atau kata sandi salah!")
        with tab2:
            with st.form("register_form"):
                new_username = st.text_input("Nama Pengguna Baru")
                new_password = st.text_input("Kata Sandi Baru", type="password")
                confirm_password = st.text_input("Konfirmasi Kata Sandi", type="password")
                if st.form_submit_button("Daftar", use_container_width=True):
                    if not (new_username and new_password and confirm_password):
                        st.error("Mohon isi semua kolom!")
                    elif new_password != confirm_password:
                        st.error("Konfirmasi kata sandi tidak cocok!")
                    elif len(new_password) < 6:
                        st.error("Kata sandi minimal 6 karakter!")
                    elif register_user(new_username, new_password):
                        st.success("Pendaftaran berhasil! Silakan masuk.")
                    else:
                        st.error("Nama pengguna sudah digunakan!")

def show_main_app():
    with st.sidebar:
        st.markdown(f"<h3 class='green-text'>👋 Selamat datang, {st.session_state.username}!</h3>", unsafe_allow_html=True)
        menu = st.selectbox("Pilih menu:", ["Deteksi", "Riwayat"])
        st.markdown("---")
        if st.button("Keluar", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()
    if menu == "Deteksi":
        detect_disease()
    else:
        show_history(st.session_state.username)

if __name__ == "__main__":
    main()