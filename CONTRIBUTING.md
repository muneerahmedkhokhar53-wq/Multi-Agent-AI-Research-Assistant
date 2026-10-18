# Contributing

Thanks for helping improve ResearchMind.

## Set up

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
cp .env.example .env             # then add your keys
streamlit run app.py
```

## Before you open a pull request

1. Run the tests: `python -m unittest discover -s tests -t . -v`
2. If you changed the look, check both light and dark mode with the button in the top bar.
3. Keep keys out of the diff. `.env` is ignored, but check anyway.

## Conventions

- **`ui.py` stays free of Streamlit imports.** HTML builders return one line with no indentation, and the stylesheet has no blank lines. Streamlit's Markdown parser turns indented or blank-line-separated HTML into a code block.
- **Colors come from CSS variables** at the top of `ui.py`. Light values are in `:root`, dark values in `_DARK`. Add a variable to both instead of hard-coding a color.
- **`options.py` and `documents.py` stay free of Streamlit imports** so they can be tested on their own. Add a test when you change them.
- Error messages shown to users say what went wrong and what to do next.

## Reporting bugs

Use the bug report template. Remove API keys from any logs you paste.
