import streamlit as st
import requests
import pandas as pd
import os
import io
from datetime import datetime

# ---- PDF GENERATION LIBRARY ----
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

# ---- CONFIG ----
API_URL = "http://localhost:8000"
CLINICAL_RULES_PATH = "For new software pre Final 7.xlsx" 
SCORING_SHEET_PATH = "Scoring excel 0 to 5 (1).csv"

# ---- PRESETS ----
ULCER_OPTIONS = ["Round Ulcer", "Irregular <1cm, <2 Weeks", "Irregular <1cm, >2 Weeks", "Irregular >1cm, <2 Weeks", "Irregular >1cm, >2 Weeks", "No Abnormality Detected"]
PATCH_OPTIONS = ["Red Patch", "White Patch", "Red & White Patch", "No Abnormality Detected", "Red patch with whitelines"]
GROWTH_OPTIONS = ["Round Growth", "Irregular Growth <1cm", "Irregular Growth >1cm", "No Abnormality Detected"]
SYMPTOM_OPTIONS = ["Pain", "Redness", "Swelling", "Burning", "Difficulty in Eating", "Blanching"]
HABIT_OPTIONS = ["Smoking", "Alcohol", "Multiple habits", "Pan Chewing", "Tobacco Chewing", "Spicy Foods"]
ORAL_MAPPING_OPTIONS = ["Buccal Mucosa", "Dorsum of Tounge", "Lateral Tongue", "Retro Molar Area", "Floor of the Mouth", "Buccal Sulcus", "Labial Mucosa", "Lip", "Palate", "Gingiva"]
MUCOSAL_OPTIONS = ["Marble Appearance", "No Abnormality Detected"]

# ---- PAGE CONFIG & CSS ----
st.set_page_config(page_title="OralDiag Pro", layout="wide", page_icon="🦷")

def local_css():
    st.markdown("""
    <style>
        .stApp { background-color: #f8f9fa; }
        section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e0e0e0; }
        div[data-testid="metric-container"] { background-color: #ffffff; border: 1px solid #e0e0e0; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .stButton>button { border-radius: 8px; font-weight: 600; }
        h1, h2, h3 { color: #2c3e50; }
        .stAlert { border-radius: 8px; }
        div[data-testid="stDataFrame"] { background-color: white; padding: 10px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# ---- SESSION STATE INITIALIZATION ----
if 'token' not in st.session_state: st.session_state.token = None
if 'current_diagnosis' not in st.session_state: st.session_state.current_diagnosis = None
if 'current_ai_result' not in st.session_state: st.session_state.current_ai_result = None
if 'final_score' not in st.session_state: st.session_state.final_score = None

# ---- LOGIC: LOADING DATA ----
@st.cache_data
def load_clinical_rules():
    if os.path.exists(CLINICAL_RULES_PATH):
        try:
            return pd.read_excel(CLINICAL_RULES_PATH, engine="openpyxl", dtype=str).fillna("")
        except: return None
    return None

@st.cache_data
def load_scoring_sheet():
    path = SCORING_SHEET_PATH
    if not os.path.exists(path):
        if os.path.exists("Scoring excel 0 to 5 (1).xlsx - Sheet1.csv"): path = "Scoring excel 0 to 5 (1).xlsx - Sheet1.csv"
        elif os.path.exists("Scoring excel 0 to 5 (1).xlsx"): path = "Scoring excel 0 to 5 (1).xlsx"
    
    if os.path.exists(path):
        try:
            if path.endswith(".csv"): df = pd.read_csv(path)
            else: df = pd.read_excel(path, engine="openpyxl")
            
            df.columns = [c.strip() for c in df.columns]
            if 'Provisional Diagnosis' in df.columns:
                df['Provisional Diagnosis'] = df['Provisional Diagnosis'].astype(str).str.strip().str.lower()
            if 'Image analysis' in df.columns:
                df['Image analysis'] = df['Image analysis'].astype(str).str.strip().str.lower()
            return df
        except Exception as e:
            st.error(f"Error loading scoring sheet: {e}")
            return None
    return None

# ---- LOGIC: SCORING ALGORITHM ----
def calculate_final_score(clinical_diag, deviation_score):
    scoring_df = load_scoring_sheet()
    if scoring_df is None: return "Error (Sheet Missing)"

    dev = float(deviation_score)
    if dev < 0.16:
        img_category = "variable diagnosis"
    elif dev <= 0.20:
        img_category = "borderline"
    else:
        img_category = "suggestive of dysplasia"

    diag_key = clinical_diag.strip().lower()
    
    match = scoring_df[
        (scoring_df['Provisional Diagnosis'] == diag_key) & 
        (scoring_df['Image analysis'].str.contains(img_category, regex=False)) 
    ]

    if not match.empty:
        return int(match.iloc[0]['Score'])
    
    return "N/A"

# ---- LOGIC: HELPER FOR CRITICALITY TEXT ----
def get_criticality_label(score):
    try:
        s = int(score)
        if s <= 1: return "Low Criticality", colors.green, "#28a745"
        elif s <= 3: return "Moderate Criticality", colors.orange, "#ffc107"
        else: return "High Criticality", colors.red, "#dc3545"
    except:
        return "Unknown", colors.black, "#6c757d"

# ---- LOGIC: PDF GENERATION ----
def create_pdf(patient_name, age, contact, clinical_data, ai_data, final_score):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("DENTAL DIAGNOSIS REPORT", styles['Title']))
    elements.append(Spacer(1, 12))

    p_data = [["Name:", patient_name, "Date:", datetime.now().strftime("%Y-%m-%d")],
              ["Age:", str(age), "Contact:", contact]]
    t = Table(p_data, colWidths=[100, 200, 50, 150])
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # Criticality Score Section
    if final_score is not None and str(final_score) != "N/A":
        label, color_obj, _ = get_criticality_label(final_score)
        elements.append(Paragraph(f"<b>CRITICALITY SCORE: <font color={color_obj}>{final_score} / 5</font></b>", styles['Heading2']))
        elements.append(Paragraph(f"<b>Assessment: <font color={color_obj}>{label}</font></b>", styles['Heading3']))
        elements.append(Spacer(1, 10))

    if clinical_data:
        elements.append(Paragraph("Clinical Observations", styles['Heading2']))
        obs_data = [[k, v] for k, v in clinical_data['inputs'].items()]
        t_obs = Table(obs_data, colWidths=[200, 300])
        t_obs.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
        elements.append(t_obs)
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"<b>Provisional:</b> {clinical_data['provisional']}", styles['BodyText']))
        elements.append(Paragraph(f"<b>Advise:</b> {clinical_data['advise']}", styles['BodyText']))
    
    if ai_data:
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Optical Analysis (Red vs Blue)", styles['Heading2']))
        if 'deviation' in ai_data: elements.append(Paragraph(f"<b>Optical Deviation Index:</b> {ai_data['deviation']}", styles['Normal']))
        if 'img_cat' in ai_data: elements.append(Paragraph(f"<b>Image Category:</b> {ai_data['img_cat'].title()}", styles['Normal']))
        if 'dl_label' in ai_data: elements.append(Paragraph(f"<b>Cancer Prediction:</b> {ai_data['dl_label']} ({ai_data['dl_conf']:.1f}%)", styles['Normal']))

    elements.append(Spacer(1, 40))
    elements.append(Paragraph("__________________________", styles['Normal']))
    elements.append(Paragraph("Doctor's Signature", styles['Normal']))
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ---- HELPER: CAMERA TRIGGER JS ----
import streamlit.components.v1 as components
def inject_camera_trigger():
    js_code = """
    <script>
    document.addEventListener('keydown', function(e) {
        if (e.code === 'F5' || e.code === 'Space' || e.code === 'Enter') {
            if (e.code === 'F5') { e.preventDefault(); }
            const buttons = window.parent.document.querySelectorAll('button');
            buttons.forEach(btn => {
                if (btn.innerText === "Capture" || btn.getAttribute("aria-label") === "Take Photo") {
                    btn.click();
                }
            });
        }
    });
    </script>
    """
    components.html(js_code, height=0, width=0)

def main():
    local_css()
    inject_camera_trigger()
    if not st.session_state.token:
        login_screen()
    else:
        dashboard_screen()

# --- LOGIN SCREEN ---
def login_screen():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br><br><h1 style='text-align: center; color: #007bff;'>🦷 OralDiag Pro</h1>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["🔐 Log In", "📝 Sign Up"])
        with tab1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Access Dashboard", type="primary", use_container_width=True):
                try:
                    res = requests.post(f"{API_URL}/token", data={"username": email, "password": password})
                    if res.status_code == 200:
                        st.session_state.token = res.json()["access_token"]
                        st.rerun()
                    else: st.error("Invalid Credentials")
                except Exception as e: st.error(f"Connection Error: {e}")
        with tab2:
            new_email = st.text_input("New Email", key="signup_email")
            new_pass = st.text_input("Set Password", type="password", key="signup_pass")
            if st.button("Create Account", use_container_width=True):
                try:
                    res = requests.post(f"{API_URL}/signup", json={"email": new_email, "password": new_pass})
                    if res.status_code == 200: st.success("Account created!")
                    else: st.error(f"Error: {res.status_code}")
                except Exception as e: st.error(f"Connection Error: {e}")

# --- DASHBOARD ---
def dashboard_screen():
    with st.sidebar:
        st.markdown("### **Dr. Workspace**")
        menu = st.radio("Navigation", ["📊 Dashboard", "➕ New Patient", "🩺 Clinical Diagnosis", "🔦 Optical Analysis", "📄 Final Report", "🚪 Logout"])
        if "Logout" in menu: st.session_state.token = None; st.rerun()

    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    # -- 1. DASHBOARD --
    if "Dashboard" in menu:
        st.title("Practice Overview")
        patients = []
        try:
            res = requests.get(f"{API_URL}/patients", headers=headers)
            if res.status_code == 200: patients = res.json()
        except: pass
        m1, m2 = st.columns(2)
        m1.metric("Total Patients", len(patients))
        m2.metric("System Status", "Online 🟢")
        if patients:
            df = pd.DataFrame(patients)
            st.dataframe(df[['id', 'name', 'age', 'gender', 'contact']], use_container_width=True, hide_index=True)

    # -- 2. NEW PATIENT --
    elif "New Patient" in menu:
        st.title("Register New Patient")
        with st.form("add_pat"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Full Name")
            gender = c1.selectbox("Gender", ["Male", "Female", "Other"])
            age = c2.number_input("Age", min_value=0)
            contact = c2.text_input("Contact")
            if st.form_submit_button("Save Record", type="primary"):
                try:
                    res = requests.post(f"{API_URL}/patients", json={"name": name, "age": age, "contact": contact, "gender": gender}, headers=headers)
                    if res.status_code == 200: st.success("Patient added!")
                    else: st.error("Failed to add.")
                except Exception as e: st.error(f"Error: {e}")

    # -- 3. CLINICAL DIAGNOSIS --
    elif "Clinical Diagnosis" in menu:
        st.title("🩺 Clinical Diagnosis")
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("Lesion Features")
            sel_ulcer = st.selectbox("Ulcer Type", ULCER_OPTIONS)
            sel_patch = st.selectbox("Patch Type", PATCH_OPTIONS)
            sel_growth = st.selectbox("Growth Type", GROWTH_OPTIONS)
        with c2:
            st.subheader("Context")
            sel_mucosa = st.selectbox("Mucosal Condition", MUCOSAL_OPTIONS)
            sel_symptoms = st.multiselect("Symptoms", SYMPTOM_OPTIONS)
            sel_habits = st.multiselect("Habits", HABIT_OPTIONS)

        if st.button("Generate Diagnosis", type="primary"):
            rules_df = load_clinical_rules()
            if rules_df is not None:
                match = False
                for _, row in rules_df.iterrows():
                    if (str(row["Ulcer"]).strip().lower() == sel_ulcer.strip().lower() and
                        str(row["Patch"]).strip().lower() == sel_patch.strip().lower() and
                        str(row["Growth"]).strip().lower() == sel_growth.strip().lower() and
                        str(row["Mucosal Condition"]).strip().lower() == sel_mucosa.strip().lower()):
                        
                        diag_data = {"inputs": {"Ulcer": sel_ulcer, "Patch": sel_patch, "Growth": sel_growth, "Symptoms": ", ".join(sel_symptoms)},
                                     "provisional": row['Provisional Diagnosis'], "differential": row['Differential Diagnosis'], "advise": row['Advise']}
                        st.session_state.current_diagnosis = diag_data
                        st.success("✅ Diagnosis Generated")
                        st.info(f"**Provisional:** {diag_data['provisional']}")
                        
                        if st.session_state.current_ai_result and 'deviation' in st.session_state.current_ai_result:
                             final = calculate_final_score(diag_data['provisional'], st.session_state.current_ai_result['deviation'])
                             st.session_state.final_score = final
                        match = True
                        break
                if not match: st.error("No match found.")
            else: st.error("Rules file missing.")

    # -- 4. OPTICAL ANALYSIS --
    elif "Optical Analysis" in menu:
        st.title("🔦 Optical Light Analysis")
        tab_ssim, tab_dl = st.tabs(["Red vs Blue Light", "Cancer Screening (DL)"])
        
        def get_img(key, label):
            opt = st.radio(f"Input {label}", ["Upload", "Camera"], horizontal=True, label_visibility="collapsed", key=f"rad_{key}")
            return st.file_uploader(f"File {key}", key=f"u_{key}") if opt=="Upload" else st.camera_input(f"Capture {label}", key=f"c_{key}")

        with tab_ssim:
            st.markdown("Compare structural differences between Red Light and Blue Light reflection.")
            c1, c2 = st.columns(2)
            with c1: 
                st.markdown("🔴 **Red Light Image**")
                img1 = get_img("ref", "Red")
            with c2: 
                st.markdown("🔵 **Blue Light Image**")
                img2 = get_img("cur", "Blue")

            if st.button("Run Optical Analysis", type="primary"):
                if img1 and img2:
                    if hasattr(img1, 'seek'): img1.seek(0)
                    if hasattr(img2, 'seek'): img2.seek(0)
                    files = {"file1": img1.getvalue(), "file2": img2.getvalue()}
                    try:
                        res = requests.post(f"{API_URL}/analyze/ssim", files=files, headers=headers)
                        if res.status_code == 200:
                            similarity = res.json()['ssim_score']
                            deviation = 1.0 - similarity
                            
                            st.markdown("### Analysis Result")
                            
                            if deviation < 0.16:
                                cat = "Variable Diagnosis"
                                status = "Low Deviation"
                                status_col = "success"
                            elif deviation <= 0.20:
                                cat = "Borderline"
                                status = "Moderate Deviation"
                                status_col = "warning"
                            else:
                                cat = "Suggestive of Dysplasia"
                                status = "Significant Deviation"
                                status_col = "error"

                            c_met, c_cat = st.columns(2)
                            c_met.metric("Optical Deviation Index", f"{deviation:.4f}")
                            if status_col == "success": c_cat.success(f"{cat} ({status})")
                            elif status_col == "warning": c_cat.warning(f"{cat} ({status})")
                            else: c_cat.error(f"{cat} ({status})")

                            if not st.session_state.current_ai_result: st.session_state.current_ai_result = {}
                            st.session_state.current_ai_result['deviation'] = deviation
                            st.session_state.current_ai_result['img_cat'] = cat
                            
                            if st.session_state.current_diagnosis:
                                final = calculate_final_score(st.session_state.current_diagnosis['provisional'], deviation)
                                st.session_state.final_score = final
                                st.info(f"Updated Criticality Score: {final}/5")
                    except: st.error("Backend Error")
                else: st.warning("Please provide both Red and Blue light images.")

        with tab_dl:
            st.markdown("Standard White Light Cancer Screening")
            dl_file = get_img("dl", "Lesion")
            if dl_file and st.button("Run Screening", type="primary"):
                dl_file.seek(0)
                files = {"file": dl_file.getvalue()}
                try:
                    res = requests.post(f"{API_URL}/analyze/dl", files=files, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        st.success(f"Result: {data['label']} ({data['confidence']:.1f}%)")
                        if not st.session_state.current_ai_result: st.session_state.current_ai_result = {}
                        st.session_state.current_ai_result['dl_label'] = data['label']
                        st.session_state.current_ai_result['dl_conf'] = data['confidence']
                except: st.error("Backend Error")

    # -- 5. FINAL REPORT --
    elif "Final Report" in menu:
        st.title("📄 Final Assessment")
        if st.session_state.final_score is not None and str(st.session_state.final_score) != "N/A":
            score = st.session_state.final_score
            label, _, hex_color = get_criticality_label(score)
            
            st.markdown(f"""
            <div style="padding: 20px; border-radius: 10px; background-color: {hex_color}; color: white; text-align: center;">
                <h2>Criticality Score</h2>
                <h1 style="font-size: 60px; margin:0; color: white;">{score} / 5</h1>
                <h3 style="margin-top:10px; color: white;">{label}</h3>
            </div>
            """, unsafe_allow_html=True)
        else:
            if st.session_state.final_score == "N/A": st.warning("Diagnosis generated, but no matching score found.")
            else: st.info("Complete Clinical Diagnosis and Optical Analysis to see the Criticality Score.")

        with st.expander("Report Details", expanded=True):
            p_name = st.text_input("Patient Name", "John Doe")
            c1, c2 = st.columns(2)
            p_age = c1.number_input("Age", 30)
            p_contact = c2.text_input("Contact", "N/A")

        if st.session_state.current_diagnosis:
            pdf_data = create_pdf(p_name, p_age, p_contact, st.session_state.current_diagnosis, st.session_state.current_ai_result, st.session_state.final_score)
            st.download_button("Download Full PDF Report", data=pdf_data, file_name="Report.pdf", mime="application/pdf", type="primary")

if __name__ == "__main__":
    main()