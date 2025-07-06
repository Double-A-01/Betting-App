
import streamlit as st
import pandas as pd
import json
import subprocess
import os
from glob import glob
from datetime import datetime

# --- Streamlit UI ---
st.title("🏇 UK Horse Racing Tips – Today")
st.markdown("Based on form, trainer stats, going, and OR rank.")
st.info("Scraping racecards using rpscrape...")

# --- Run scraper ---
try:
    result = subprocess.run(
        ["python3", "rpscrape/scripts/racecards.py"],
        capture_output=True, text=True, check=True
    )
    st.success("racecards.py ran successfully")
    st.code(result.stdout, language='bash')
except subprocess.CalledProcessError as e:
    st.error("Scraper failed!")
    st.code(e.stderr, language='bash')
    st.stop()

# --- List files to debug JSON output ---
st.subheader("Files in rpscrape/scripts/")
st.code(os.listdir("rpscrape/scripts"))

# --- Load the latest racecards JSON ---
try:
    json_file = sorted(glob("rpscrape/scripts/racecards-*.json"))[-1]
    with open(json_file, "r") as f:
        data = json.load(f)
except Exception as e:
    st.error("No racecards JSON found. Scraper might not have created it.")
    st.stop()

# --- Scoring logic ---
def score_runner(runner, trainer_strike=0.10):
    score = 0
    if runner.get("last_finish", 0) <= 3:
        score += 1
    if runner.get("trainer_strike", 0) >= trainer_strike:
        score += 1
    if runner.get("going_match", False):
        score += 1
    if runner.get("or_rank", 99) <= 3:
        score += 1
    return score

# --- Parse and score runners ---
tips = []
for meeting in data.get("meetings", []):
    if meeting.get("region") != "gb":
        continue

    course = meeting["course"]
    for race in meeting["races"]:
        race_time = race.get("time", "")
        going = race.get("going", "")
        runners = []

        for r in race.get("runners", []):
            runner = {
                "course": course,
                "time": race_time,
                "going": going,
                "runner_name": r.get("name", ""),
                "trainer": r.get("trainer", ""),
                "jockey": r.get("jockey", ""),
                "draw": r.get("draw", ""),
                "odds": r.get("odds", ""),
                "last_finish": r.get("form", [9])[0] if isinstance(r.get("form", [9]), list) else 9,
                "trainer_strike": r.get("trainer_strike", 0),
                "going_match": r.get("going", "").lower() in going.lower(),
                "or_rank": r.get("or", 99)
            }
            runner["score"] = score_runner(runner)
            runners.append(runner)

        df = pd.DataFrame(runners)
        df = df[df["score"] >= 2].sort_values("score", ascending=False).head(2)
        tips.extend(df.to_dict("records"))

# --- Show results ---
if tips:
    df_final = pd.DataFrame(tips)
    st.success(f"Top {len(df_final)} tips generated for today!")
    st.dataframe(df_final[[
        "course", "time", "runner_name", "trainer", "jockey", "odds", "score"
    ]])
else:
    st.warning("No qualifying tips found for today based on the current rules.")
