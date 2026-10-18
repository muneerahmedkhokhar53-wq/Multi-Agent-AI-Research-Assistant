"""Presentation layer for ResearchMind.

Pure Python: no Streamlit import, so the CSS and markup can be tested on their own.
Every HTML builder returns a single line with no indentation, because Streamlit's
markdown parser turns indented or blank-line-separated HTML into a code block.
"""

from __future__ import annotations

import html
import re
import zlib
from urllib.parse import urlparse

# ── Pipeline definition ──────────────────────────────────────────────────────
STEPS = [
    ("search", "Search agent", "Finds recent sources on the web"),
    ("reader", "Reader agent", "Opens the best source and reads it"),
    ("writer", "Writer", "Drafts the report from what was found"),
    ("critic", "Critic", "Scores the report and flags gaps"),
]

# Each agent has its own colour and glyph.
STEP_STYLE = {
    "search": ("#1f9bd1", "🔎"),
    "reader": ("#3a56c8", "📖"),
    "writer": ("#ff8000", "✍️"),
    "critic": ("#f0a040", "🧐"),
}

EXAMPLES = [
    "How close is fusion energy to powering a grid?",
    "What CRISPR therapies are approved today?",
    "How do LLM agents handle long-running tasks?",
]

PALETTE = ["#1f9bd1", "#3a56c8", "#ff8000", "#f0a040"]

FONT_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Poppins:wght@300;400;500;600;700;800&display=swap"
)

# ── Stylesheet ───────────────────────────────────────────────────────────────
# White page, near-black text, one orange accent (#ff8000). Light is the default;
# dark mode is switched on by the button in the top bar (see DARK_CSS below).
# Rules for our own classes are written plainly and prefixed with ".stApp" by
# _scope() below, so they always out-rank Streamlit's built-in element styles.
_CSS = """
@import url('__FONT_URL__');

:root {
  color-scheme: light;
  --bg: #ffffff;
  --card: #ffffff;
  --card-2: #f4f4f4;
  --line: rgba(28, 28, 28, .12);
  --line-2: rgba(28, 28, 28, .3);
  --text: #1c1c1c;
  --muted: #737373;
  --on-brand: #ffffff;
  --orange: #ff8000;
  --orange-d: #e67300;
  --g1: #ff9a2e;
  --g2: #ff8000;
  --g3: #f27600;
  --g4: #e66c00;
  --t-search: #1f93c4;
  --t-reader: #3a56c8;
  --t-writer: #e67300;
  --t-critic: #b8741a;
  --off-bg: #f4f4f4;
  --off-line: #d9d9d9;
  --shadow: 0 24px 50px -34px rgba(28, 28, 28, .35);
  --mint: #059669;
  --danger: #e11d48;
  --tint-a: rgba(167, 220, 239, .22);
  --tint-b: rgba(255, 190, 140, .16);
  --brand: linear-gradient(100deg, var(--g1) 0%, var(--g2) 50%, var(--g4) 100%);
  --sans: 'Poppins', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
  --serif: 'Poppins', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
}

/* ── Page ── */
.stApp { background: radial-gradient(900px 640px at 0% 14%, var(--tint-a), transparent 72%), radial-gradient(800px 600px at 100% 24%, var(--tint-b), transparent 72%), var(--bg) !important; background-attachment: fixed !important; color: var(--text); }
.stApp::before { content: ""; position: fixed; top: 0; left: 0; right: 0; height: 3px; background: #4f444a; z-index: 1000; }
.stApp [data-testid="stAppViewContainer"], .stApp [data-testid="stMain"] { background: transparent !important; }
.stApp [data-testid="stHeader"] { background: transparent !important; }
.stApp #MainMenu, .stApp footer, .stApp [data-testid="stToolbar"], .stApp [data-testid="stDecoration"] { visibility: hidden; }
.stApp .block-container { max-width: 1120px; padding: 1.5rem 2rem 5rem !important; }
.stApp ::selection { background: var(--g2); color: #fff; }

/* Fonts: Streamlit sets its own face on every text element, so set ours on the same elements. */
.stApp, .stApp :is(p, li, div, label, input, textarea, button, a, h1, h2, h3, h4, h5, h6, summary, td, th, small, strong, em):not([data-testid="stIconMaterial"]):not(code) {
  font-family: var(--sans);
}

/* ── Masthead ── */
.masthead { display: flex; align-items: center; gap: .8rem; padding: .25rem 0 0; }
.mark { flex: none; display: inline-grid; place-items: center; width: 46px; height: 46px; border-radius: 50%; background: var(--orange); color: #ffffff; font-weight: 700; font-size: 1.3rem; line-height: 1; }
.wordmark { font-weight: 700; font-size: 1.5rem; letter-spacing: -.02em; color: var(--text); }

/* ── Hero ── */
.hero { padding: 4rem 0 2.25rem; }
.pill { display: inline-flex; align-items: center; padding: 0; background: none; border: 0; font-size: 1.2rem; font-weight: 500; color: var(--orange); animation: rise .7s cubic-bezier(.2, .7, .2, 1) both; }
.live { display: none; }
.hero h1 { margin: 1.2rem 0 1.5rem; padding: 0; font-weight: 700; font-size: clamp(2.4rem, 5.8vw, 4.3rem); line-height: 1.2; letter-spacing: -.035em; color: var(--text); max-width: 16em; }
.h1-a { display: block; margin-bottom: .12em; animation: rise .8s .1s cubic-bezier(.2, .7, .2, 1) both; }
.h1-b { display: inline-block; max-width: 100%; padding: .02em .25em .1em; background: var(--text); color: var(--bg); -webkit-text-fill-color: var(--bg); animation: rise .8s .22s cubic-bezier(.2, .7, .2, 1) both; }
.hero p { margin: 0; max-width: 36em; font-size: 1.15rem; line-height: 1.7; color: var(--muted); animation: rise .8s .36s cubic-bezier(.2, .7, .2, 1) both; }

/* ── Ask form ── */
.stApp [data-testid="stForm"] { background: var(--card) !important; border: 1px solid var(--line) !important; border-radius: 30px !important; padding: 1rem !important; box-shadow: var(--shadow); }
.stApp [data-testid="stForm"] [data-testid="stHorizontalBlock"] { align-items: center; gap: .75rem; }
.stApp [data-testid="stTextInputRootElement"] { height: 3.6rem; background: var(--bg) !important; border: 1.5px solid var(--line-2) !important; border-radius: 999px !important; transition: border-color .2s, box-shadow .2s; }
.stApp [data-testid="stTextInputRootElement"]:focus-within { border-color: var(--g2) !important; box-shadow: 0 0 0 4px rgba(255, 128, 0, .2) !important; }
.stApp .stTextInput [data-baseweb="input"], .stApp .stTextInput [data-baseweb="base-input"] { background: transparent !important; border: 0 !important; height: 100%; }
.stApp .stTextInput input { height: 100% !important; background: transparent !important; border: 0 !important; color: var(--text) !important; -webkit-text-fill-color: var(--text); font-size: 1.05rem !important; padding: 0 1.6rem !important; }
.stApp .stTextInput input::placeholder { color: var(--muted) !important; -webkit-text-fill-color: var(--muted); opacity: 1; }

.stApp [data-testid="stFormSubmitButton"] button, .stApp .stFormSubmitButton button {
  width: 100%; height: 3.6rem; border: 0 !important; border-radius: 999px !important;
  background: var(--orange) !important; color: #ffffff !important;
  font-weight: 700 !important; font-size: 1.02rem !important; box-shadow: none !important;
  transition: background .3s, color .3s, transform .2s;
}
.stApp [data-testid="stFormSubmitButton"] button:hover, .stApp .stFormSubmitButton button:hover { background: var(--orange-d) !important; color: #ffffff !important; transform: translateY(-2px); }
.stApp [data-testid="stFormSubmitButton"] button p, .stApp .stFormSubmitButton button p, .stApp [data-testid="stDownloadButton"] button p, .stApp .st-key-theme_toggle button p, .stApp .st-key-examples .stButton button p { font: inherit !important; color: inherit !important; -webkit-text-fill-color: currentColor; }
.stApp button:focus-visible, .stApp input:focus-visible { outline: 3px solid rgba(255, 128, 0, .5) !important; outline-offset: 2px; }

.try-label { margin: 1.4rem 0 .6rem; font-size: .95rem; color: var(--muted); }
.stApp .st-key-examples [data-testid="stHorizontalBlock"] { gap: .7rem; }
.stApp .st-key-examples .stButton button { height: auto; min-height: 3rem; padding: .6rem 1rem; background: transparent !important; color: var(--text) !important; border: 2px solid var(--text) !important; border-radius: 28px !important; font-weight: 600 !important; font-size: .93rem !important; line-height: 1.35; text-align: center; box-shadow: none !important; transition: transform .2s, border-color .2s; }
.stApp .st-key-examples .stButton button:hover { transform: translateY(-3px); background: var(--text) !important; color: var(--bg) !important; }

/* ── Pipeline: four agents, driven by real task status ── */
.route-card { position: relative; overflow: hidden; margin-top: 2.5rem; padding: 1.7rem 1.9rem 2.3rem; background: var(--card); border: 1px solid var(--line); border-radius: 26px; box-shadow: var(--shadow); }
.route-head { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: .5rem 1rem; margin-bottom: 1.9rem; }
.route-title { display: inline-block; margin: 0; padding: 0; font-size: 1.3rem; font-weight: 800; line-height: 1.3; letter-spacing: -.02em; color: var(--g2); background: var(--brand); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.route-meta { font-size: .93rem; font-weight: 500; color: var(--muted); }
.route { --o: 84px; list-style: none; margin: 0 !important; padding: 0 !important; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }
.station { position: relative; list-style: none; margin: 0 !important; padding: calc(var(--o) + 28px) 1rem 0 0 !important; }
.station.s-search { --ct: var(--t-search); }
.station.s-reader { --ct: var(--t-reader); }
.station.s-writer { --ct: var(--t-writer); }
.station.s-critic { --ct: var(--t-critic); }

/* Connector to the next agent: faint when waiting, a travelling spark while the agent works, filled when done */
.station:not(:last-child)::before { content: ""; position: absolute; top: calc(var(--o) / 2 - 2px); left: calc(var(--o) + 20px); right: 12px; height: 4px; border-radius: 4px; background: var(--line); }
.station.is-done:not(:last-child)::before { background: linear-gradient(90deg, var(--c), var(--cn)); }
.station.is-running:not(:last-child)::before { background-color: var(--line); background-image: linear-gradient(90deg, transparent, var(--c), transparent); background-size: 45% 100%; background-repeat: no-repeat; background-position: -60% 0; animation: comet 1.9s ease-in-out infinite; }

/* The agent: halo, ring, face, check */
.orb { position: absolute; top: 0; left: 0; width: var(--o); height: var(--o); border-radius: 50%; }
.orb .halo { position: absolute; inset: 0; border-radius: 50%; background: var(--c); opacity: 0; pointer-events: none; }
.orb .arc { position: absolute; inset: -9px; border-radius: 50%; background: var(--line); -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 calc(100% - 2px)); mask: radial-gradient(farthest-side, transparent calc(100% - 3px), #000 calc(100% - 2px)); }
.orb .face { position: relative; width: 100%; height: 100%; display: grid; place-items: center; border-radius: 50%; font-size: calc(var(--o) * .4); background: var(--off-bg); border: 1.5px solid var(--off-line); filter: grayscale(.85); opacity: .55; box-shadow: 0 0 30px -12px var(--c); }
.station.is-running .orb .face, .station.is-done .orb .face { filter: none; opacity: 1; border-color: transparent; background: radial-gradient(circle at 30% 20%, rgba(255, 255, 255, .65), transparent 55%), linear-gradient(145deg, var(--c), var(--cn)); }
.station.is-done .orb .face { box-shadow: 0 12px 28px -10px var(--c); }
.station.is-done .orb .arc { background: linear-gradient(135deg, var(--c), var(--cn)); }
.station.is-running .orb .arc { background: conic-gradient(from 0deg, transparent 0 58%, var(--c) 100%); animation: spin 1.3s linear infinite; }
.station.is-running .orb .face { animation: ignite .9s ease-out both, breathe 2.4s .9s ease-in-out infinite; }
.station.is-running .orb .halo { animation: halo 2.4s ease-out infinite; }
.station.is-running .orb .halo.h2 { animation-delay: 1.2s; }
.station.is-failed .orb .face { filter: none; opacity: 1; background: var(--card-2); border-color: var(--danger); box-shadow: 0 10px 30px -10px var(--danger); }
.station.is-failed .orb .arc { background: var(--danger); }
.check { position: absolute; right: -3px; bottom: -3px; z-index: 2; display: none; place-items: center; width: 26px; height: 26px; border-radius: 50%; background: var(--text); color: var(--bg); font-size: .8rem; font-weight: 800; box-shadow: 0 4px 12px rgba(0, 0, 0, .35); }
.station.is-done .check { display: grid; }

/* The moment an agent finishes: its glow lets go and a single ring leaves it */
.station.is-fresh .orb .face { animation: settle 1.1s cubic-bezier(.2, .8, .2, 1) both; }
.station.is-fresh .orb::after { content: ""; position: absolute; inset: -9px; border-radius: 50%; border: 3px solid var(--c); animation: burst .95s ease-out both; }
.station.is-fresh .check { animation: pop .6s .25s cubic-bezier(.3, 1.6, .5, 1) both; }

/* Entrance: all four arrive together, glowing softly */
.route.is-intro .orb { animation: enter .95s cubic-bezier(.2, .9, .25, 1.1) both; }
.route.is-intro .station-name, .route.is-intro .station-desc, .route.is-intro .station-status { animation: rise .8s .2s cubic-bezier(.2, .7, .2, 1) both; }

.station-name { font-size: 1.15rem; font-weight: 800; letter-spacing: -.015em; color: var(--ct); }
.station-desc { margin-top: .25rem; max-width: 15em; font-size: .93rem; line-height: 1.5; color: var(--muted); }
.station-status { display: inline-flex; align-items: center; margin-top: .85rem; padding: .3rem .75rem; border-radius: 999px; background: var(--card-2); font-size: .82rem; font-weight: 700; color: var(--muted); }
.station.is-running .station-status, .station.is-done .station-status { color: var(--ct); }
.station.is-failed .station-status { color: var(--danger); }
.dots i { display: inline-block; width: 4px; height: 4px; margin-left: 3px; border-radius: 50%; background: currentColor; animation: blink 1.2s infinite both; }
.dots i:nth-child(2) { animation-delay: .2s; }
.dots i:nth-child(3) { animation-delay: .4s; }
.bar { position: absolute; left: 0; right: 0; bottom: 0; height: 5px; background: var(--line); }
.bar span { display: block; height: 100%; border-radius: 0 5px 5px 0; background: var(--brand); background-size: 200% 100%; }
.bar.is-live span { animation: flow 3s linear infinite; }

/* ── Notices ── */
.notice { margin-top: 1.5rem; max-width: 48rem; padding: 1.1rem 1.4rem; background: var(--card); border: 1px solid var(--line); border-left: 4px solid var(--danger); border-radius: 14px; }
.notice strong { display: block; margin-bottom: .3rem; color: var(--text); font-size: 1.05rem; }
.notice p { margin: 0; color: var(--muted); line-height: 1.55; font-size: .98rem; }
.notice code { padding: .1em .4em; border-radius: 5px; background: var(--card-2); color: var(--text); font-size: .86em; word-break: break-word; }

/* ── Results ── */
.result-head { margin: 4rem 0 1.4rem; }
.result-head::before { content: ""; display: block; height: 2px; margin-bottom: 2.2rem; background: var(--brand); border-radius: 2px; }
.result-head h2 { margin: 0 0 .6rem; padding: 0; max-width: 22em; font-weight: 800; font-size: clamp(1.9rem, 4.2vw, 3rem); line-height: 1.08; letter-spacing: -.04em; color: var(--g2); background: var(--brand); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.result-head p { margin: 0; color: var(--muted); font-size: 1rem; }

.stApp [data-baseweb="tab-list"] { gap: .25rem !important; width: fit-content; padding: .3rem !important; background: var(--card); border: 1px solid var(--line); border-radius: 999px; }
.stApp button[data-baseweb="tab"] { height: auto !important; padding: .55rem 1.25rem !important; background: transparent !important; border: 0 !important; border-radius: 999px !important; transition: background .2s; }
.stApp button[data-baseweb="tab"] p { font-weight: 600; font-size: .98rem !important; color: var(--muted) !important; }
.stApp button[data-baseweb="tab"]:hover p { color: var(--text) !important; }
.stApp button[data-baseweb="tab"][aria-selected="true"] { background: var(--orange) !important; }
.stApp button[data-baseweb="tab"][aria-selected="true"] p { color: #ffffff !important; }
.stApp [data-baseweb="tab-highlight"], .stApp [data-baseweb="tab-border"] { display: none !important; }

/* Report: a white sheet in both modes, serif body, colourful headings */
.stApp .st-key-report { position: relative; overflow: hidden; margin-top: 1.4rem; padding: 3rem clamp(1.25rem, 4.5vw, 3.5rem) 2.5rem; background: #ffffff; border: 1px solid var(--line); border-radius: 24px; box-shadow: var(--shadow); }
.stApp .st-key-report::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 6px; background: #ff8000; }
.stApp .st-key-report [data-testid="stMarkdownContainer"] :is(p, li, ul, ol, strong, em, blockquote, td, th) { font-family: var(--serif); font-size: 1.05rem; line-height: 1.8; color: #1c1c1c; }
.stApp .st-key-report [data-testid="stMarkdownContainer"] :is(p, li) { max-width: 68ch; }
.stApp .st-key-report li { margin-bottom: .45rem; }
.stApp .st-key-report :is(h1, h2, h3, h4) { padding: 0; font-weight: 700; letter-spacing: -.03em; line-height: 1.2; color: #1c1c1c; }
.stApp .st-key-report :is(h1, h2) { width: fit-content; max-width: 100%; color: #1c1c1c; }
.stApp .st-key-report h1 { font-size: 2.2rem; margin: .5rem 0 1rem; }
.stApp .st-key-report h2 { font-size: 1.7rem; margin: 2.5rem 0 .7rem; }
.stApp .st-key-report h3 { font-size: 1.25rem; margin: 1.9rem 0 .5rem; }
.stApp .st-key-report a { color: #e67300 !important; text-underline-offset: 3px; word-break: break-word; }
.stApp .st-key-report blockquote { margin: 1.4rem 0; padding: .2rem 0 .2rem 1.2rem; border-left: 4px solid #ff8000; }
.stApp .st-key-report hr { border: 0; border-top: 1px solid #e6e6e6; margin: 2.2rem 0; }
.stApp [data-testid="stDownloadButton"] button { height: 3rem; margin-top: 1.25rem; padding: 0 1.5rem; background: var(--orange) !important; color: #ffffff !important; border: 0 !important; border-radius: 999px !important; font-weight: 700 !important; box-shadow: none !important; transition: transform .2s, background .3s, color .3s; }
.stApp [data-testid="stDownloadButton"] button:hover { transform: translateY(-2px); background: var(--orange-d) !important; color: #ffffff !important; }

/* Review: a score ring that fills in */
@property --p { syntax: '<number>'; inherits: false; initial-value: 0; }
.stApp .st-key-review { margin-top: 1.4rem; padding: 2rem clamp(1.25rem, 3.5vw, 2.5rem); background: var(--card); border: 1px solid var(--line); border-radius: 24px; }
.stApp .st-key-review [data-testid="stMarkdownContainer"] { font-size: 1.05rem; line-height: 1.65; max-width: 64ch; color: var(--text); }
.score { display: flex; align-items: center; gap: 1.75rem; flex-wrap: wrap; margin-bottom: 1.75rem; }
.ring { --p: 0; display: grid; place-items: center; width: 136px; height: 136px; border-radius: 50%; background: radial-gradient(closest-side, var(--card) 80%, transparent 82%), conic-gradient(from 0deg, var(--g1), var(--g2) calc(var(--p) * .45%), var(--g3) calc(var(--p) * .8%), var(--g4) calc(var(--p) * 1%), var(--line) calc(var(--p) * 1%)); animation: fill 1.6s .2s cubic-bezier(.2, .7, .2, 1) both; }
.ring span { font-size: 2.6rem; font-weight: 800; letter-spacing: -.05em; color: var(--text); }
.ring small { font-size: 1rem; font-weight: 600; letter-spacing: 0; color: var(--muted); margin-left: .1rem; }
.tier { width: fit-content; font-size: 1.7rem; font-weight: 800; letter-spacing: -.035em; color: var(--g2); background: var(--brand); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.score-sub { margin-top: .2rem; color: var(--muted); font-size: .98rem; }

/* Sources */
.sources { list-style: none; margin: 1.5rem 0 2rem; padding: 0 !important; max-width: 50rem; display: grid; gap: .7rem; }
.sources li { margin: 0; }
.source { display: flex; align-items: center; gap: 1rem; padding: .85rem 1.1rem; background: var(--card); border: 1px solid var(--line); border-radius: 16px; text-decoration: none; color: var(--text); transition: transform .2s, border-color .2s; }
.source:hover { transform: translateY(-2px); border-color: var(--c); }
.source:focus-visible { outline: 3px solid rgba(255, 128, 0, .5); outline-offset: 2px; }
.badge { flex: none; display: grid; place-items: center; width: 42px; height: 42px; border-radius: 12px; background: var(--c); color: #ffffff; font-weight: 800; font-size: 1.1rem; }
.src-text { min-width: 0; }
.src-domain { display: block; font-weight: 700; }
.src-url { display: block; font-size: .86rem; color: var(--muted); overflow-wrap: anywhere; }
.sources-empty { margin: 1.5rem 0; color: var(--muted); }
.raw { margin: 0; max-height: 26rem; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; font-family: var(--sans); font-size: .95rem; line-height: 1.6; color: var(--muted); }
.stApp [data-testid="stExpander"] { background: var(--card); border: 1px solid var(--line) !important; border-radius: 16px !important; }
.stApp [data-testid="stExpander"] summary p { font-weight: 600; }
.stApp [data-testid="stAlert"] { border-radius: 14px; }

.colophon { margin-top: 5rem; padding-top: 1.25rem; border-top: 1px solid var(--line); color: var(--muted); font-size: .92rem; }

/* ── Documents and options inside the form ── */
.stApp .stTextInput input:-webkit-autofill, .stApp .stTextInput input:-webkit-autofill:hover, .stApp .stTextInput input:-webkit-autofill:focus { -webkit-box-shadow: 0 0 0 1000px var(--bg) inset !important; -webkit-text-fill-color: var(--text) !important; caret-color: var(--text); transition: background-color 9999s ease-out 0s; }
.stApp [data-testid="stForm"] [data-testid="stExpander"] { margin-top: .85rem; background: var(--bg); border: 1px solid var(--line) !important; border-radius: 16px !important; }
.stApp [data-testid="stForm"] [data-testid="stExpander"] summary { padding: .95rem 1.2rem; }
.stApp [data-testid="stForm"] [data-testid="stExpander"] summary p { font-weight: 700; }
.stApp [data-testid="stWidgetLabel"] p { font-weight: 600; font-size: .92rem; color: var(--text); }
.stApp [data-testid="stFileUploaderDropzone"] { background: var(--card); border: 1.5px dashed var(--line-2); border-radius: 16px; transition: border-color .2s, background .2s; }
.stApp [data-testid="stFileUploaderDropzone"]:hover { border-color: var(--g2); }
.stApp [data-testid="stFileUploaderDropzone"] button { border-radius: 10px; border: 1px solid var(--line-2); background: var(--bg); color: var(--text); }
.stApp [data-baseweb="select"] > div { background: var(--bg) !important; border: 1px solid var(--line-2) !important; border-radius: 12px !important; }
.stApp textarea { background: var(--bg) !important; border: 1px solid var(--line-2) !important; border-radius: 12px !important; color: var(--text) !important; font-size: .98rem !important; }
.stApp textarea:focus { border-color: var(--g2) !important; box-shadow: 0 0 0 3px rgba(255, 128, 0, .2) !important; }

/* Summary of the options used for a run */
.chips { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1rem; }
.chip { padding: .3rem .8rem; border: 1px solid var(--line); border-radius: 999px; background: var(--card); font-size: .85rem; font-weight: 600; color: var(--muted); }

/* Uploaded documents */
.docs-title { margin: 2rem 0 0; font-size: 1.05rem; font-weight: 800; color: var(--text); }
.docs { list-style: none; margin: 1rem 0 1.5rem; padding: 0 !important; display: grid; gap: .6rem; max-width: 50rem; }
.doc { display: flex; align-items: center; gap: .9rem; margin: 0; padding: .75rem 1rem; background: var(--card); border: 1px solid var(--line); border-radius: 14px; }
.doc-ext { flex: none; display: grid; place-items: center; min-width: 46px; height: 34px; border-radius: 9px; background: var(--card-2); font-size: .74rem; font-weight: 800; color: var(--text); }
.doc-name { display: block; font-weight: 700; color: var(--text); overflow-wrap: anywhere; }
.doc-note { display: block; font-size: .86rem; color: var(--muted); }
.doc.is-error { border-color: var(--danger); }
.doc.is-error .doc-note { color: var(--danger); }

/* A step left out of this run: dimmed, with a dashed label */
.station.is-skipped .station-name, .station.is-skipped .station-desc { opacity: .55; }
.station.is-skipped .station-status { background: transparent; border: 1px dashed var(--line-2); }

/* Reports in right-to-left languages: each paragraph follows its own direction */
.stApp .st-key-report [data-testid="stMarkdownContainer"] :is(p, li, h1, h2, h3, h4, blockquote) { unicode-bidi: plaintext; }

/* ── Theme toggle ── */
.stApp .st-key-theme_toggle button { height: 3rem; border: 0 !important; border-radius: 999px !important; background: var(--orange) !important; color: #ffffff !important; font-weight: 600 !important; font-size: .98rem !important; box-shadow: none !important; transition: background .25s, transform .2s; }
.stApp .st-key-theme_toggle button:hover { background: var(--orange-d) !important; color: #ffffff !important; transform: translateY(-2px); }

/* ── Streamlit's own widgets follow the chosen theme, not the system one ── */
.stApp textarea::placeholder { color: var(--muted) !important; opacity: 1; }
.stApp :is([data-testid="stAlert"], [data-testid="stAlert"] *) { color: var(--text) !important; }
.stApp [data-testid="stAlert"] { background: var(--card-2) !important; border: 1px solid var(--line); }
.stApp [data-testid="stExpander"] summary, .stApp [data-testid="stExpander"] summary * { color: var(--text); }
.stApp [data-baseweb="select"] * { color: var(--text) !important; }
.stApp [data-baseweb="select"] svg { fill: var(--muted); }
.stApp [data-baseweb="radio"] *, .stApp [data-testid="stToggle"] label * { color: var(--text) !important; }
.stApp :is([data-testid="stTickBarMin"], [data-testid="stTickBarMax"]) { color: var(--muted) !important; }
.stApp [data-testid="stFileUploaderDropzone"] :is(span, small, div) { color: var(--muted) !important; }
.stApp [data-testid="stFileUploaderDropzone"] button, .stApp [data-testid="stFileUploaderDropzone"] button * { color: var(--text) !important; }
.stApp .st-key-review [data-testid="stMarkdownContainer"] :is(p, li, h1, h2, h3, h4, strong, em, td, th, blockquote) { color: var(--text); }
.stApp .st-key-review code, .stApp [data-testid="stMarkdownContainer"] code { background: var(--card-2); color: var(--text); }
[data-baseweb="popover"] > div, [data-baseweb="popover"] ul, [data-baseweb="menu"] { background: var(--card) !important; color: var(--text) !important; }
[data-baseweb="popover"] li, [data-baseweb="popover"] li * { color: var(--text) !important; }
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] { background: var(--card-2) !important; }

/* ── Motion ── */
@keyframes rise { from { opacity: 0; transform: translateY(22px); } }
@keyframes flow { to { background-position: 200% 0; } }
@keyframes ripple { from { transform: scale(1); opacity: .7; } to { transform: scale(3.2); opacity: 0; } }
@keyframes bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-4px); } }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes blink { 0%, 80%, 100% { opacity: .2; } 40% { opacity: 1; } }
@keyframes pop { 0% { transform: scale(.4); opacity: 0; } 60% { transform: scale(1.15); } 100% { transform: scale(1); opacity: 1; } }
@keyframes fill { from { --p: 0; } }
@keyframes enter { from { opacity: 0; transform: translateY(18px) scale(.55); filter: blur(8px); } to { opacity: 1; transform: none; filter: blur(0); } }
@keyframes ignite { from { filter: grayscale(.85); opacity: .55; transform: scale(.94); } to { filter: grayscale(0); opacity: 1; transform: scale(1); } }
@keyframes breathe { 0%, 100% { box-shadow: 0 0 26px 2px var(--c); } 50% { box-shadow: 0 0 66px 12px var(--c); } }
@keyframes halo { from { transform: scale(1); opacity: .42; } to { transform: scale(1.9); opacity: 0; } }
@keyframes settle { from { transform: scale(1.14); box-shadow: 0 0 74px 14px var(--c); } to { transform: scale(1); box-shadow: 0 12px 28px -10px var(--c); } }
@keyframes burst { from { transform: scale(1); opacity: .9; } to { transform: scale(1.55); opacity: 0; } }
@keyframes comet { from { background-position: -60% 0; } to { background-position: 160% 0; } }
@keyframes cometY { from { background-position: 0 -60%; } to { background-position: 0 160%; } }

/* ── Small screens ── */
@media (max-width: 760px) {
  .stApp .block-container { padding: 1rem 1.1rem 4rem !important; }
  .hero { padding: 2.5rem 0 1.5rem; }
  .route-card { padding: 1.3rem 1.2rem 1.9rem; }
  .route { --o: 64px; grid-template-columns: 1fr; }
  .station { min-height: var(--o); padding: 0 0 2rem calc(var(--o) + 24px) !important; }
  .station:last-child { padding-bottom: 0 !important; }
  .station:not(:last-child)::before { top: calc(var(--o) + 14px); bottom: 6px; left: calc(var(--o) / 2 - 2px); right: auto; width: 4px; height: auto; }
  .station.is-done:not(:last-child)::before { background: linear-gradient(180deg, var(--c), var(--cn)); }
  .station.is-running:not(:last-child)::before { background-image: linear-gradient(180deg, transparent, var(--c), transparent); background-size: 100% 45%; background-position: 0 -60%; animation: cometY 1.9s ease-in-out infinite; }
  .station-desc { max-width: none; }
  .ring { width: 116px; height: 116px; }
  .ring span { font-size: 2.2rem; }
}

@media (prefers-reduced-motion: reduce) {
  .stApp *, .stApp *::before, .stApp *::after { animation: none !important; transition: none !important; }
  .stApp .station.is-running .orb .face { box-shadow: 0 0 0 6px rgba(255, 128, 0, .25), 0 0 40px 4px var(--c); }
}
""".replace("__FONT_URL__", FONT_URL)

_CUSTOM = re.compile(
    r"^\.(masthead|mark|wordmark|hero|pill|live|h1-a|h1-b|try-label|route|station|orb|check|dots|bar|"
    r"notice|result-head|score|ring|tier|sources|source|badge|src|raw|colophon|chips|chip|docs|doc)\b"
)


def _scope(css: str) -> str:
    """Prefix selectors that start with one of our own classes with '.stApp '."""
    out = []
    for line in css.split("\n"):
        m = re.match(r"^(\s*)([^@{}\s/][^{}]*?)\s*\{(.*)$", line)
        if m:
            parts = [p.strip() for p in m.group(2).split(",")]
            parts = [f".stApp {p}" if _CUSTOM.match(p) else p for p in parts]
            line = f"{m.group(1)}{', '.join(parts)} {{{m.group(3)}"
        out.append(line)
    return "\n".join(out)


def _minify(css: str) -> str:
    """One line, no comments. Markdown ends an HTML block at the first blank line, so the
    stylesheet must never contain one or the rest of it is printed as page text."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return re.sub(r"\s+", " ", css).strip()


CSS = _minify(_scope(_CSS))

# Dark mode: the same variables, redefined. Appended after the light rules so it wins.
_DARK = """
:root {
  color-scheme: dark;
  --bg: #131313;
  --card: #1c1c1c;
  --card-2: #272727;
  --line: rgba(255, 255, 255, .14);
  --line-2: rgba(255, 255, 255, .32);
  --text: #f5f5f5;
  --muted: #a3a3a3;
  --g1: #ffa646;
  --t-search: #6cc9f0;
  --t-reader: #8fa3ff;
  --t-writer: #ff9a33;
  --t-critic: #f5b868;
  --off-bg: #222222;
  --off-line: #3a3a3a;
  --shadow: 0 24px 50px -30px rgba(0, 0, 0, .9);
  --mint: #34d399;
  --danger: #fb7185;
  --tint-a: rgba(167, 220, 239, .07);
  --tint-b: rgba(255, 128, 0, .09);
}
"""
DARK_CSS = _minify(_DARK)

THEMES = ("light", "dark")


def stylesheet(theme: str = "light") -> str:
    # Starts with <style> (a raw-text HTML block) and is a single line.
    return f"<style>{CSS}{DARK_CSS if theme == 'dark' else ''}</style>"


def theme_button_label(theme: str) -> str:
    """The toggle names the mode it switches to."""
    return "☀️ Light mode" if theme == "dark" else "🌙 Dark mode"


# ── Markup builders ──────────────────────────────────────────────────────────
def masthead_html() -> str:
    return (
        '<div class="masthead"><span class="mark" aria-hidden="true">R</span>'
        '<span class="wordmark">ResearchMind</span></div>'
    )


def hero_html() -> str:
    return (
        '<div class="hero"><div class="pill"><span class="live" aria-hidden="true"></span>Four agents ready</div>'
        '<h1><span class="h1-a">Ask a question.</span><span class="h1-b">Four agents do the reading.</span></h1>'
        "<p>A searcher, a reader, a writer and a critic work through your topic in turn, "
        "then hand you a sourced report and an honest review of it.</p></div>"
    )


def try_label_html() -> str:
    return '<div class="try-label">Try one of these</div>'


def route_html(
    states: dict[str, str],
    timings: dict[str, float] | None = None,
    fresh: str | None = None,
    intro: bool = False,
) -> str:
    """states maps step key -> waiting | running | done | failed.

    Every visual state comes from `states`, which the app sets from real task status.
    `fresh` marks the step that just finished (its glow settles once).
    `intro` plays the one-time entrance; leave it off for later updates so the
    circles don't re-enter on every status change.
    """
    timings = timings or {}
    keys = [k for k, _, _ in STEPS]
    items = []
    for i, (key, name, desc) in enumerate(STEPS):
        state = states.get(key, "waiting")
        color, glyph = STEP_STYLE[key]
        next_color = STEP_STYLE[keys[i + 1]][0] if i + 1 < len(keys) else color
        if state == "done":
            status = html.escape(f"Done in {timings[key]:.0f}s" if key in timings else "Done")
        elif state == "running":
            status = 'Working<span class="dots" aria-hidden="true"><i></i><i></i><i></i></span>'
        elif state == "failed":
            status = "Stopped with an error"
        elif state == "skipped":
            status = "Skipped"
        else:
            status = "Waiting"
        cls = f"station is-{state} s-{key}" + (" is-fresh" if fresh == key and state == "done" else "")
        current = ' aria-current="step"' if state == "running" else ""
        items.append(
            f'<li class="{cls}"{current} style="--c:{color};--cn:{next_color}">'
            '<div class="orb" aria-hidden="true"><span class="halo"></span><span class="halo h2"></span>'
            f'<span class="arc"></span><span class="face">{glyph}</span><span class="check">✓</span></div>'
            f'<div class="station-name">{html.escape(name)}</div>'
            f'<div class="station-desc">{html.escape(desc)}</div>'
            f'<div class="station-status">{status}</div></li>'
        )
    done = sum(1 for k in keys if states.get(k) == "done")
    skipped = sum(1 for k in keys if states.get(k) == "skipped")
    total = len(keys) - skipped
    running = any(states.get(k) == "running" for k in keys)
    pct = round((done + (0.5 if running else 0)) / total * 100)
    return (
        '<div class="route-card"><div class="route-head"><h2 class="route-title">Agent pipeline</h2>'
        f'<span class="route-meta">{done} of {total} steps done</span></div>'
        f'<ol class="route{" is-intro" if intro else ""}" aria-label="Research progress">{"".join(items)}</ol>'
        f'<div class="bar{" is-live" if running else ""}" aria-hidden="true"><span style="width:{pct}%"></span></div></div>'
    )


def notice_html(title: str, body: str) -> str:
    """Body may contain trusted inline markup (e.g. <code>); escape untrusted text first."""
    return f'<div class="notice" role="alert"><strong>{html.escape(title)}</strong><p>{body}</p></div>'


def result_head_html(topic: str, total_seconds: float | None, chips: list[str] | None = None) -> str:
    meta = f"Researched in {total_seconds:.0f} seconds by the agents." if total_seconds else ""
    pills = (
        '<div class="chips">' + "".join(f'<span class="chip">{html.escape(c)}</span>' for c in chips) + "</div>"
        if chips else ""
    )
    return (
        f'<div class="result-head"><h2>{html.escape(topic)}</h2>'
        f"{f'<p>{meta}</p>' if meta else ''}{pills}</div>"
    )


def docs_html(rows: list[dict]) -> str:
    """One row per uploaded file: how much was read, or why it couldn't be."""
    items = []
    for r in rows:
        ext = html.escape(r["name"].rsplit(".", 1)[-1][:4].upper()) if "." in r["name"] else "FILE"
        if "error" in r:
            note, cls = html.escape(r["error"]), "doc is-error"
        elif r["truncated"]:
            note, cls = f"Read the first {r['used']:,} of {r['chars']:,} characters", "doc"
        else:
            note, cls = f"Read in full ({r['chars']:,} characters)", "doc"
        items.append(
            f'<li class="{cls}"><span class="doc-ext" aria-hidden="true">{ext}</span>'
            f'<span><span class="doc-name">{html.escape(r["name"])}</span><span class="doc-note">{note}</span></span></li>'
        )
    return f'<h3 class="docs-title">Your documents</h3><ul class="docs">{"".join(items)}</ul>'



_SCORE_RE = re.compile(r"^\s*\**\s*Score\s*:?\s*\**\s*(\d+(?:\.\d+)?)\s*/\s*10\s*\**\s*$", re.I | re.M)


def parse_score(feedback: str) -> tuple[float | None, str]:
    """Pull 'Score: X/10' out of the critic's text. Returns (score, remaining text)."""
    m = _SCORE_RE.search(feedback)
    if not m:
        return None, feedback
    score = max(0.0, min(10.0, float(m.group(1))))
    rest = (feedback[: m.start()] + feedback[m.end():]).strip()
    return score, rest


def score_html(score: float) -> str:
    shown = f"{score:g}"
    tier = "Strong report" if score >= 8 else "Solid report" if score >= 6 else "Needs more work"
    return (
        f'<div class="score" role="img" aria-label="Critic score {shown} out of 10">'
        f'<div class="ring" style="--p:{score * 10:g}"><span>{html.escape(shown)}<small>/10</small></span></div>'
        f'<div><div class="tier">{tier}</div><div class="score-sub">The critic’s overall rating</div></div></div>'
    )


_URL_RE = re.compile(r"https?://[^\s<>\"'\)\]]+")


def extract_urls(*texts: str) -> list[str]:
    seen: dict[str, None] = {}
    for text in texts:
        for url in _URL_RE.findall(text or ""):
            url = url.rstrip(".,;:*")
            if urlparse(url).netloc:
                seen.setdefault(url, None)
    return list(seen)


def sources_html(urls: list[str]) -> str:
    if not urls:
        return '<p class="sources-empty">No source links were found in the agents’ output.</p>'
    rows = []
    for url in urls:
        host = urlparse(url).netloc.removeprefix("www.")
        color = PALETTE[zlib.crc32(host.encode()) % len(PALETTE)]
        rows.append(
            f'<li><a class="source" style="--c:{color}" href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">'
            f'<span class="badge" aria-hidden="true">{html.escape(host[:1].upper())}</span>'
            f'<span class="src-text"><span class="src-domain">{html.escape(host)}</span>'
            f'<span class="src-url">{html.escape(url)}</span></span></a></li>'
        )
    return f'<ul class="sources">{"".join(rows)}</ul>'


def raw_html(text: str) -> str:
    return f'<pre class="raw">{html.escape(text)}</pre>'


def colophon_html() -> str:
    return '<div class="colophon">ResearchMind runs a LangChain pipeline, with Tavily for search.</div>'
