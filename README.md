# FanDuel Optimizer

A mobile-friendly Streamlit app for generating multiple FanDuel tournament lineups from a slate CSV or sample data.

## Features

- Upload a FanDuel CSV slate
- Generate multiple lineup combinations with player locks and exclusions
- Enforce lineup constraints and salary limits
- Produce a downloadable CSV of the generated lineups
- Works with sample player data if no CSV is uploaded

## Local development

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:
   ```bash
   streamlit run app.py
   ```

4. Open the app in your browser at:
   ```text
   http://localhost:8501
   ```

## Notes

- The app uses `pulp` for optimization and `streamlit` for the UI.
- If you upload your own CSV, include at least these columns:
  - `Player`
  - `Position`
  - `Team`
  - `Salary`
  - `Projection`
  - `StdDev` (optional; defaults to 25% of projection if missing)

## Default app behavior

If no CSV is uploaded, the app loads a sample slate so you can test the interface immediately.
