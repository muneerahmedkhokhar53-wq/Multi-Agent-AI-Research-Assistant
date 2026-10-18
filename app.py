import html
import os
import re
import time

import streamlit as st

import documents
import options
import ui

st.set_page_config(
    page_title="ResearchMind",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.session_state.setdefault("theme", "light")
st.markdown(ui.stylesheet(st.session_state.theme), unsafe_allow_html=True)

# tools.py builds the Tavily client on import, so a missing key fails here.
try:
    from agents import build_reader_agent, build_search_agent, writer_chain, critic_chain
    BACKEND_ERROR = None
except Exception as exc:  # noqa: BLE001 - shown to the user, not swallowed
    BACKEND_ERROR = exc


# ── Session state ────────────────────────────────────────────────────────────
DEFAULTS = {
    "results": {},      # step key -> output text
    "timings": {},      # step key -> seconds
    "topic_run": "",    # topic the current results belong to
    "failed": None,     # (step key, message) if a step raised
    "pending": None,    # topic queued by an example button
    "skipped": [],      # step keys left out of this run (documents-only mode)
    "docs_report": [],  # one row per uploaded file: what was read, or why not
    "run_meta": {},     # summary chips for the current results
}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)


def toggle_theme() -> None:
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"


def queue_example(topic: str) -> None:
    st.session_state.topic_input = topic
    st.session_state.pending = topic


def step_states() -> dict[str, str]:
    results, failed, skipped = st.session_state.results, st.session_state.failed, st.session_state.skipped
    states = {}
    for key, _, _ in ui.STEPS:
        if key in results:
            states[key] = "done"
        elif key in skipped:
            states[key] = "skipped"
        elif failed and failed[0] == key:
            states[key] = "failed"
        else:
            states[key] = "waiting"
    return states


def run_pipeline(topic: str, slot, cfg: dict) -> None:
    """Run the steps in order, updating the progress route as each one starts and ends."""
    skip = {"search", "reader"} if cfg["docs_only"] else set()

    def search():
        agent = build_search_agent()
        out = agent.invoke({"messages": [("user", f"Find recent, reliable and detailed information about: {topic}")]})
        return out["messages"][-1].content

    def read():
        agent = build_reader_agent()
        prompt = options.reader_prompt(topic, results.get("search", ""), cfg["urls"])
        out = agent.invoke({"messages": [("user", prompt)]})
        return out["messages"][-1].content

    def write():
        parts = []
        if "search" in results:
            parts.append(f"SEARCH RESULTS:\n{results['search']}")
        if "reader" in results:
            parts.append(f"DETAILED SCRAPED CONTENT:\n{results['reader']}")
        if cfg["material"]:
            parts.append(f"USER-PROVIDED DOCUMENTS:\n{cfg['material']}")
        return writer_chain.invoke({"topic": topic + cfg["instructions"], "research": "\n\n".join(parts)})

    def critique():
        return critic_chain.invoke({"report": results["writer"]})

    runners = {"search": search, "reader": read, "writer": write, "critic": critique}

    results: dict[str, str] = {}
    timings: dict[str, float] = {}
    st.session_state.update(
        results={}, timings={}, topic_run=topic, failed=None, skipped=sorted(skip),
        docs_report=cfg["docs_report"], run_meta={"chips": cfg["chips"]},
    )

    prev = None
    for key, _, _ in ui.STEPS:
        if key in skip:
            continue
        states = {k: "done" if k in results else "skipped" if k in skip else "waiting" for k, _, _ in ui.STEPS}
        states[key] = "running"
        slot.markdown(ui.route_html(states, timings, fresh=prev, intro=prev is None), unsafe_allow_html=True)

        started = time.time()
        try:
            results[key] = runners[key]()
        except Exception as exc:  # noqa: BLE001
            st.session_state.failed = (key, f"{type(exc).__name__}: {exc}")
            break
        timings[key] = time.time() - started
        st.session_state.results = dict(results)
        st.session_state.timings = dict(timings)
        prev = key

    slot.markdown(
        ui.route_html(step_states(), st.session_state.timings, fresh=prev if not st.session_state.failed else None),
        unsafe_allow_html=True,
    )


# ── Header and ask form ──────────────────────────────────────────────────────
with st.container(key="topbar"):
    bar_left, bar_right = st.columns([5, 1.6], vertical_alignment="center")
    with bar_left:
        st.markdown(ui.masthead_html(), unsafe_allow_html=True)
    with bar_right:
        st.button(
            ui.theme_button_label(st.session_state.theme),
            key="theme_toggle",
            on_click=toggle_theme,
            use_container_width=True,
        )
st.markdown(ui.hero_html(), unsafe_allow_html=True)

with st.form("ask", border=False):
    col_in, col_btn = st.columns([5, 1.2], vertical_alignment="bottom")
    with col_in:
        topic_value = st.text_input(
            "Research topic",
            placeholder="e.g. How close is fusion energy to powering a grid?",
            key="topic_input",
            label_visibility="collapsed",
            autocomplete="off",
        )
    with col_btn:
        submitted = st.form_submit_button("Start research", use_container_width=True)

    with st.expander("Add documents and options"):
        files = st.file_uploader(
            "Documents to include",
            type=documents.SUPPORTED,
            accept_multiple_files=True,
            key="docs",
            help="PDF, Word, text, Markdown or CSV. The writer uses them alongside the web research.",
        )
        left, right = st.columns(2)
        with left:
            style = st.selectbox("Report style", list(options.STYLES), key="opt_style")
            language = st.selectbox("Language", options.LANGUAGES, key="opt_language")
            depth = st.radio(
                "Search depth", options.SEARCH_DEPTHS, horizontal=True, key="opt_depth",
                help="Advanced digs deeper on each search and uses more of your Tavily credits.",
            )
        with right:
            audience = st.selectbox("Audience", list(options.AUDIENCES), key="opt_audience")
            n_results = st.slider("Web results per search", 3, 10, 5, key="opt_results")
            budget = st.slider(
                "Characters read from documents", 2000, documents.MAX_BUDGET, documents.DEFAULT_BUDGET,
                step=1000, key="opt_budget",
                help="Free model plans limit how much text they accept per minute. Raise this only if your plan allows it.",
            )
        urls_text = st.text_area(
            "Pages to read first",
            key="opt_urls",
            height=88,
            placeholder="One link per line. The reader agent opens these instead of choosing a page itself.",
            help="Up to three links.",
        )
        docs_only = st.toggle(
            "Use only my documents and skip the web",
            key="opt_docs_only",
            help="Skips the search and reader agents. Needs at least one document.",
        )

st.markdown(ui.try_label_html(), unsafe_allow_html=True)
with st.container(key="examples"):
    for col, example in zip(st.columns(len(ui.EXAMPLES)), ui.EXAMPLES):
        with col:
            st.button(example, key=f"ex_{example}", on_click=queue_example, args=(example,), use_container_width=True)


def prepare(topic: str) -> dict | None:
    """Turn the form into a run configuration, or say why the run can't start and return None."""
    files_data = [(f.name, f.getvalue()) for f in (files or [])]
    material, rows = documents.build_material(files_data, budget) if files_data else ("", [])
    st.session_state.docs_report = rows

    if docs_only and not material:
        st.warning(
            "Add at least one document to use documents only."
            if not files_data else "None of the documents could be read, so there's nothing to research. See the notice below."
        )
        return None

    # The search tool reads these each time it runs.
    os.environ["SEARCH_MAX_RESULTS"] = str(n_results)
    os.environ["SEARCH_DEPTH"] = depth.lower()

    urls = [] if docs_only else options.parse_urls(urls_text)
    read_ok = sum(1 for r in rows if "error" not in r)
    chips = []
    if style != "Standard report":
        chips.append(style)
    if audience != "General reader":
        chips.append(f"For a {audience.lower()}")
    if language != "English":
        chips.append(language)
    if read_ok:
        chips.append(f"{read_ok} document{'s' if read_ok != 1 else ''}")
    if docs_only:
        chips.append("Documents only")
    else:
        if depth == "Advanced":
            chips.append("Advanced search")
        if n_results != 5:
            chips.append(f"{n_results} results per search")
        if urls:
            chips.append(f"{len(urls)} chosen page{'s' if len(urls) != 1 else ''}")

    return {
        "material": material,
        "docs_report": rows,
        "docs_only": docs_only,
        "urls": urls,
        "instructions": options.writing_instructions(style, audience, language, bool(material)),
        "chips": chips,
    }


# ── Decide whether to run ────────────────────────────────────────────────────
topic_to_run = st.session_state.pending
st.session_state.pending = None
if submitted:
    topic_to_run = (topic_value or "").strip()
    if not topic_to_run:
        st.warning("Enter a research topic to start.")

cfg = prepare(topic_to_run) if topic_to_run else None

route_slot = st.empty()

if cfg is not None and BACKEND_ERROR is None:
    run_pipeline(topic_to_run, route_slot, cfg)
else:
    idle = not st.session_state.results and not st.session_state.failed
    route_slot.markdown(
        ui.route_html(step_states(), st.session_state.timings, intro=idle), unsafe_allow_html=True
    )

# ── Errors ───────────────────────────────────────────────────────────────────
if BACKEND_ERROR is not None:
    st.markdown(
        ui.notice_html(
            "The research agents couldn’t start",
            "Check that <code>LLM_API_KEY</code> (or <code>OPENAI_API_KEY</code>) and <code>TAVILY_API_KEY</code> are set in a "
            "<code>.env</code> file next to <code>app.py</code>, then reload. "
            f"Details: <code>{html.escape(str(BACKEND_ERROR))}</code>",
        ),
        unsafe_allow_html=True,
    )

failed = st.session_state.failed
if failed:
    names = {k: n for k, n, _ in ui.STEPS}
    st.markdown(
        ui.notice_html(
            f"{names[failed[0]]} stopped",
            "The steps after it didn’t run. Check your API keys and network connection, then start again. "
            f"Details: <code>{html.escape(failed[1])}</code>",
        ),
        unsafe_allow_html=True,
    )

unreadable = [r for r in st.session_state.docs_report if "error" in r]
if unreadable:
    st.markdown(
        ui.notice_html(
            "Some documents couldn’t be read",
            "<br>".join(f"<code>{html.escape(r['name'])}</code> {html.escape(r['error'])}" for r in unreadable),
        ),
        unsafe_allow_html=True,
    )

# ── Results ──────────────────────────────────────────────────────────────────
results = st.session_state.results

if results:
    timings = st.session_state.timings
    total = sum(timings.values()) if "critic" in results else None
    st.markdown(
        ui.result_head_html(st.session_state.topic_run, total, st.session_state.run_meta.get("chips")),
        unsafe_allow_html=True,
    )

    tab_report, tab_review, tab_sources = st.tabs(["Report", "Review", "Sources"])

    with tab_report:
        if "writer" in results:
            with st.container(key="report"):
                st.markdown(results["writer"])
            slug = re.sub(r"[^a-z0-9]+", "-", st.session_state.topic_run.lower()).strip("-")[:48] or "report"
            st.download_button(
                "Download report (.md)",
                data=results["writer"],
                file_name=f"{slug}.md",
                mime="text/markdown",
            )
        else:
            st.info("The report appears here once the writer finishes.")

    with tab_review:
        if "critic" in results:
            score, body = ui.parse_score(results["critic"])
            with st.container(key="review"):
                if score is not None:
                    st.markdown(ui.score_html(score), unsafe_allow_html=True)
                st.markdown(body)
        else:
            st.info("The critic’s review appears here after the report is written.")

    with tab_sources:
        urls = ui.extract_urls(results.get("search", ""), results.get("reader", ""), results.get("writer", ""))
        if urls or not st.session_state.docs_report:
            st.markdown(ui.sources_html(urls), unsafe_allow_html=True)
        if st.session_state.docs_report:
            st.markdown(ui.docs_html(st.session_state.docs_report), unsafe_allow_html=True)
        if "search" in results:
            with st.expander("What the search agent found"):
                st.markdown(ui.raw_html(results["search"]), unsafe_allow_html=True)
        if "reader" in results:
            with st.expander("What the reader agent extracted"):
                st.markdown(ui.raw_html(results["reader"]), unsafe_allow_html=True)

st.markdown(ui.colophon_html(), unsafe_allow_html=True)
