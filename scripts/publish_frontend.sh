mkdir -p docs/results/

# Copy supporting files
cp frontend/docs/magical_athlete_analysis.css docs/
cp results/{races,racer_results}.parquet docs/results/


# Export the notebook
uvx marimo export html-wasm --mode run --no-show-code \
  frontend/magical_athlete_analysis.py \
  -o docs
