# main.py
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
body { font-family: Inter, Arial, sans-serif; ma...