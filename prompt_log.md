# Log 2025-12-15 09:32
# cv_maker_app.py
import streamlit as st
import pdfplumber, base64, tempfile, re, os, json
from weasyprint import HTML
from openai import OpenAI
from jinja2 import Environment, FileSystemLoader

# --- AI client ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Automatische mappen en templates ---
TEMPLATE_DIR = "templates"
os.makedirs(TEMPLATE_DIR, exist_ok=True)

TEMPLATE_FILES = {
    "modern.html": """<!doctype html><html><head><meta charset="utf-8"/>
<style>
:root { --accent: {{ accent }}; --accent-contrast:#fff; --text:#111827; --bg:#ffffff; }
body { font-family: Inter, Arial, sans-serif; margin:0; color:var(--text); }
.layout { display:flex; min-height:100vh; }
.sidebar { width:30%; background:var(--accent); color:var(--accent-contrast); padding:20px; }
.sidebar img { width:120px; height:120px; border-radius:60px; margin-bottom:20px; }
.main { flex:1; padding:40px; }
h2 { color:var(--accent); border-bottom:1px solid #e5e7eb; padding-bottom:4px; }
</style></head><body>
<div class="layout">
  <div class="sidebar">
    {% if data.photo %}<img src="data:image/png;base64,{{ data.photo }}"/>{% endif %}
    <h2>{{ data.name }}</h2>
    <p>{{ data.address }}</p>
    <p>{{ data.email }}</p>
    <h3>Skills</h3>
    <ul>{% for s in data.skills %}<li>{{ s }}</li>{% endfor %}</ul>
  </div>
  <div class="main">
    <h2>Ervaring</h2>
    <div>{{ data.experience | replace('\\n','<br/>') | safe }}</div>
    <h2>Opleiding</h2>
    <div>{{ data.education }}</div>
  </div>
</div>
</body></html>""",
    "classic.html": """<!doctype html><html><head><meta charset="utf-8"/>
<style>
:root { --accent: {{ accent }}; }
body { font-family: "Times New Roman", serif; margin:0; }
.layout { display:flex; }
.sidebar { width:25%; background:var(--accent); color:#fff; padding:20px; }
.main { flex:1; padding:40px; }
h2 { color:var(--accent); }
</style></head><body>
<div class="layout">
  <div class="sidebar">
    {% if data.photo %}<img src="data:image/png;base64,{{ data.photo }}" style="width:100px;height:100px;border-radius:50%;"/>{% endif %}
    <h2>{{ data.name }}</h2>
    <p>{{ data.address }}</p>
    <p>{{ data.email }}</p>
    <h3>Skills</h3>
    <ul>{% for s in data.skills %}<li>{{ s }}</li>{% endfor %}</ul>
  </div>
  <div class="main">
    <h2>Ervaring</h2>
    <div>{{ data.experience | replace('\\n','<br/>') | safe }}</div>
    <h2>Opleiding</h2>
    <div>{{ data.education }}</div>
  </div>
</div>
</body></html>""",
    "ats.html": """<!doctype html><html><head><meta charset="utf-8"/>
<style>
body { font-family: Arial, sans-serif; margin:40px; }
h1 { font-size:20px; } h2 { font-size:14px; margin-top:12px; }
</style></head><body>
<h1>{{ data.name }}</h1>
<p>{{ data.address }}</p>
<p>{{ data.email }}</p>
<h2>Ervaring</h2><div>{{ data.experience | replace('\\n','<br/>') | safe }}</div>
<h2>Opleiding</h2><div>{{ data.education }}</div>
<h2>Skills</h2><ul>{% for s in data.skills %}<li>{{ s }}</li>{% endfor %}</ul>
</body></html>"""
}

# Schrijf templates naar bestanden
for fname, content in TEMPLATE_FILES.items():
    fpath = os.path.join(TEMPLATE_DIR, fname)
    if not os.path.exists(fpath):
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content.strip())

# --- Paletten ---
PALETTES = {
    "Neutral": "#374151","Blue": "#2b6cb0","Green": "#059669",
    "Warm": "#b45309","Monochrome": "#111827","High Contrast": "#000000"
}

# --- Helpers ---
def file_to_base64(file) -> str:
    return base64.b64encode(file.read()).decode("utf-8")

def extract_cv_data(file_obj):
    text = ""
    try:
        with pdfplumber.open(file_obj) as pdf:
            pages = [p.extract_text() for p in pdf.pages]
            text = " ".join([p for p in pages if p])
    except Exception:
        try: text = file_obj.read().decode("utf-8", errors="ignore")
        except Exception: text = ""
    data = {"name":"","experience":"","education":"","skills":[]}
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if lines: data["name"] = lines[0]
    skills_keywords = ["Python","JavaScript","SQL","Docker","Kubernetes","AWS","Git"]
    data["skills"] = [k for k in skills_keywords if k.lower() in text.lower()]
    exp_match = re.search(r"(Experience|Ervaring)(.*?)(Education|Opleiding|Skills|$)", text, re.S|re.I)
    if exp_match: data["experience"] = exp_match.group(2).strip()
    edu_match = re.search(r"(Education|Opleiding)(.*?)(Skills|$)", text, re.S|re.I)
    if edu_match: data["education"] = edu_match.group(2).strip()
    return data

def render_pdf(data, template_name, accent):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    tpl = env.get_template(template_name)
    html = tpl.render(data=data, accent=accent)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    HTML(string=html).write_pdf(tmp.name)
    return tmp.name, html

def improve_text(text, style="concise", language="nl", template="modern.html"):
    if not text.strip(): return []
    prompt = (
        f"Verbeter deze CV-tekst zodat hij {style}, ATS-vriendelijk en in {language} is. "
        f"Template: {template}. Geef drie varianten: formeel, neutraal, creatief.\n\n"
        f"Tekst:\n{text}\n\nAntwoord in JSON array."
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        max_tokens=400, temperature=0.6
    )
    content = resp.choices[0].message.content
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list): return parsed
    except Exception:
        return [p.strip() for p in content.split("\n") if p.strip()][:3]
    return []

# --- Streamlit UI ---
st.set_page_config(page_title="CV Maker", layout="wide")
st.title("CV Maker App")

st.sidebar.header("Instellingen")
template_choice = st.sidebar.selectbox("Kies template", list(TEMPLATE_FILES.keys()))
palette_choice = st.sidebar.selectbox("Kleurpalet", list(PALETTES.keys())+["Custom"])
accent = st.sidebar.color_picker("Kies accentkleur", "#2b6cb0") if palette_choice=="Custom" else PALETTES[palette_choice]
uploaded_pdf = st.sidebar.file_uploader("Upload bestaande CV (PDF)", type="pdf")
uploaded_photo = st.sidebar.file_uploader("Upload profielfoto", type=["jpg","jpeg","png"])

# Data input
if uploaded_pdf:
    parsed = extract_cv_data(uploaded_pdf)
    data = {"name": parsed.get("name",""),"experience": parsed.get("experience",""),
            "education": parsed.get("education",""),"skills": parsed.get("skills",[])}
    st.success("CV data geïmporteerd uit PDF")
else:
    data = {"name": st.text_input("Naam"),
            "address": st.text_input("Adres"),
            "email": st.text_input("E-mail"),
            "experience": st.text_area