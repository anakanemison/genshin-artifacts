import os
import pandas as pd
import re
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

API_KEY = os.environ['GOOGLE_API_KEY']
SPREADSHEET_ID = '1gNxZ2xab1J6o1TuNVWMeLOZ7TPOqrsf3SshP5DLvKzI'

# Initialize Google Sheets API
service = build('sheets', 'v4', developerKey=API_KEY)
sheet = service.spreadsheets()

# Fetch data
response = service.spreadsheets().values().batchGet(
    spreadsheetId=SPREADSHEET_ID,
    ranges=[
        "Pyro !A1:J",
        "Electro !A1:J",
        "Dendro!A1:J",
        "Hydro !A1:J",
        "Cryo !A1:J",
        "Anemo !A1:J",
        "Geo !A1:J",
    ]
).execute()

# Elemental types in the same order as the ranges list
elements = ["PYRO", "ELECTRO", "DENDRO", "HYDRO", "CRYO", "ANEMO", "GEO"]

dfs = []

for i, value_range in enumerate(response['valueRanges']):
    df = pd.DataFrame(value_range['values'])

    # Rename TRAVELER rows in column 1
    df.iloc[:, 1] = df.iloc[:, 1].apply(
        lambda x: f"{elements[i]} TRAVELER" if isinstance(x, str) and x.startswith("TRAVELER") else x
    )

    # Trim the first 5 rows (0-indexed)
    df_trimmed = df.iloc[5:].reset_index(drop=True)
    dfs.append(df_trimmed)

# Concatenate all the trimmed dataframes into one final dataframe
df_trimmed = pd.concat(dfs, ignore_index=True)

# Step 2: Filter out unwanted rows (e.g., "4 STAR", "5 STAR", "NOTES", and "Last Updated:" rows)
filter_keywords = ["4 STAR", "5 STAR", "NOTES"]

df_cleaned = df_trimmed[
    ~df_trimmed[1].isin(filter_keywords) & 
    ~df_trimmed[1].astype(str).str.startswith("Last Updated:")
].reset_index(drop=True)

# Step 3: Identify character blocks (non-empty strings in column '1' are character names)
parsed_blocks = []
current_character = None

for _, row in df_cleaned.iterrows():
    if isinstance(row[1], str) and row[1]:  # If column '1' has a non-empty string
        current_character = row[1]
    if current_character:
        parsed_blocks.append({
            "Character": current_character,
            "Role": row[2],
            "Artifact Sets": row[4],
            "Main Stats": row[5],
            "Substats": row[6]
        })

# Step 4: Convert parsed blocks into a DataFrame
df_parsed = pd.DataFrame(parsed_blocks)

# Step 5: Filter rows to retain only those with meaningful data
df_final_cleaned = df_parsed[
    df_parsed[['Role', 'Artifact Sets', 'Main Stats', 'Substats']]
    .notnull()
    .any(axis=1)
].reset_index(drop=True)

# Normalize multiline text fields, collapse multiple spaces
for col in ['Artifact Sets', 'Main Stats', 'Substats']:
    df_final_cleaned[col] = df_final_cleaned[col].apply(
        lambda x: re.sub(r' +', ' ', x).splitlines() if isinstance(x, str) else []
    )

def concatenate_tilde_lines(lines):
    processed_lines = []
    for i, line in enumerate(lines):
        line = line.strip()
        # If needed concatenate with the previous line using " / "
        if line.startswith('~=') and processed_lines:
            processed_lines[-1] += ' / ' + line[2:].strip()
        elif line.startswith('≈') and processed_lines:
            processed_lines[-1] += ' / ' + line[1:].strip()
        else:
            processed_lines.append(line)
    return processed_lines

df_final_cleaned['Artifact Sets'] = df_final_cleaned['Artifact Sets'].apply(concatenate_tilde_lines)
df_final_cleaned['Substats'] = df_final_cleaned['Substats'].apply(concatenate_tilde_lines)

# Helper functions for enhanced processing
def clean_and_split_artifact_set_names(artifact_sets_names_text):
    replacements = [
        # Use "|" as a consistent separator
        ["/", "|"],
        ["+", "|"],
        [" and ", "|"],  # ...risky. Seems likely to end up in an artifact set name someday
        ["~=", "|"],
        ["≈", "|"],
        ["(2)", "|"],  # number parentheticals sometimes act as separators
        ["(4)", "|"],

        # Remove garbage
        ["[Choose One]", ""],  
        ["[Choose Two]", ""],
        ["[Choose two]", ""],
        ["[see notes]", ""],
        ["Mixes of", ""],
        ["Furina Teams only, performs as well or better than Nighttime Whispers in the Echoing Woods", ""],
        ["Other damaging options (see DPS)", ""],
        ["*", ""],

        # Canonicalize names
        ["15% Anemo DMG Set", "15% Anemo DMG set"],
        ["15% Healing Bonus", "15% Healing Bonus set"],
        ["15% Healing Bonus set set", "15% Healing Bonus set"],  # alas
        ["15% Hydro DMG Bonus set", "15% Hydro DMG set"],
        ["18 ATK% set", "18% ATK set"],
        ["18% ATK Set", "18% ATK set"],
        ["20% ER set", "20% Energy Recharge set"],
        ["20% HP", "20% HP set"],
        ["20% HP set set", "20% HP set"],  # alas again
        ["80 EM", "80 EM set"],
        ["80 EM set set", "80 EM set"],  # alas again again
        ["Emblem Of Severed Fate", "Emblem of Severed Fate"],
        ["Marechausse Hunter", "Marechaussee Hunter"],
        ["Ocean Hued Clam", "Ocean-Hued Clam"],

        # Set category expansions; assume only 5 star sets matter
        ["15% Anemo DMG set", "15% Anemo DMG set|Viridescent Venerer|Desert Pavilion Chronicle"],
        ["15% Healing Bonus set", "15% Healing Bonus set|Maiden Beloved|Ocean-Hued Clam|Song of Days Past"],
        ["15% Hydro DMG set", "15% Hydro DMG set|Heart of Depth|Nymph's Dream"],
        ["18% ATK set", "18% ATK set|Gladiator's Finale|Shimenawa's Reminiscence|Vermillion Hereafter|Echoes of an Offering|Nighttime Whispers in the Echoing Woods|Fragment of Harmonic Whimsy|Unfinished Reverie"],
        ["20% Energy Recharge set", "20% Energy Recharge set|Emblem of Severed Fate"],
        ["20% HP set", "20% HP set|Tenacity of the Millelith|Vourukasha's Glow"],
        ["25% Physical DMG set", "25% Physical DMG set|Bloodstained Chivalry|Pale Flame"],
        ["80 EM set", "80 EM set|Wanderer's Troupe|Gilded Dreams|Flower of Paradise Lost"],
    ]
    for r in replacements:
        artifact_sets_names_text = artifact_sets_names_text.replace(r[0], r[1])
    artifact_sets_names_text = artifact_sets_names_text.strip()

    ns = [name.strip() for name in artifact_sets_names_text.split("|") if name]
    seen = {"", "Any", "set"}  # don't include meaningless artifact set text
    uniques = []
    for n in ns:
        if n not in seen:
            uniques.append(n)
            seen.add(n)
    return uniques

def clean_and_split_stats(stat):
    if not isinstance(stat, str):
        return []
    
    # Remove extraneous text
    stat = re.sub(r'\(.*?\)', '', stat)
    stat = re.sub(r'\[.*?\]', '', stat)
    stat = stat.replace("*", "")
    stat = stat.replace("until requirement is met", "")
    stat = stat.replace("until requirement", "")

    # Canonicalize naming
    stat = stat.replace("Atk%", "ATK%")
    stat = stat.replace("Anemo Damage", "Anemo DMG")
    stat = stat.replace("Crit Rate%", "Crit Rate")
    stat = stat.replace("CRIT Rate", "Crit Rate")
    stat = stat.replace("CRIT", "Crit Rate|Crit DMG")
    stat = stat.replace("Cryo DMG%", "Cryo DMG")
    stat = stat.replace("Electro Damage", "Electro DMG")
    stat = stat.replace("Electro DMG%", "Electro DMG")
    stat = stat.replace("Energy Recharge%", "Energy Recharge")
    stat = stat.replace("ER%", "Energy Recharge")
    stat = stat.replace("Flat DEF", "DEF")
    stat = stat.replace("Geo DMG%", "Geo DMG")
    stat = stat.replace("Healing Bonus%", "Healing Bonus")
    stat = stat.replace("Physical DMG%", "Physical DMG")
    stat = stat.replace("Pyro DMG%", "Pyro DMG")

    separators = ["/", "+", " and ", "~=", "=", "≈"]
    for sep in separators:
        stat = stat.replace(sep, "|")  # Use a consistent delimiter
    return [("Crit DMG" if s.strip() == "DMG" else s.strip()) for s in stat.split("|") if s.strip()]

def extract_rank(text):
    if isinstance(text, str) and text.strip():
        parts = text.split(".", 1)
        if len(parts) == 2 and parts[0].isdigit():
            return int(parts[0]), parts[1].strip()
    return None, text.strip() if isinstance(text, str) else text

# Enhanced data processing
enhanced_data_v2 = []

for _, row in df_final_cleaned.iterrows():
    character = row["Character"]
    preferred_role = "✩" in row["Role"] if isinstance(row["Role"], str) else False
    role = re.sub(r'[\r\n]+', ' ', row["Role"]).replace("✩", "").strip()
    artifact_sets_lines = row["Artifact Sets"]
    main_stat_lines = row["Main Stats"]
    substat_lines = row["Substats"]

    for artifact_sets_line in artifact_sets_lines:
        artifact_rank, artifact_set_names_text = extract_rank(artifact_sets_line)
        if artifact_rank is None:
            continue
        artifact_set_names = clean_and_split_artifact_set_names(artifact_set_names_text)
        for artifact_set_name in artifact_set_names:
            for main_stat_line in main_stat_lines:
                # Split main stats by slashes and clean
                slot_stat_parts = main_stat_line.split(" - ")
                slot = slot_stat_parts[0].strip() if len(slot_stat_parts) > 1 else None
                if slot is None:
                    continue
                main_stats = clean_and_split_stats(slot_stat_parts[1]) if len(slot_stat_parts) > 1 else []
                for stat in main_stats:
                    for substat_line in substat_lines:
                        substat_rank, substat_text = extract_rank(substat_line)
                        if substat_rank is None:
                            continue
                        substat_names = clean_and_split_stats(substat_text)
                        for substat_name in substat_names:
                            if stat == substat_name:
                                continue  # Skip duplicate main and substats; can't be rolled
                            enhanced_data_v2.append({
                                "Character": character,
                                "Role": role,
                                "Preferred Role": preferred_role,
                                "Artifact Set": artifact_set_name,
                                "Artifact Set Rank": artifact_rank,
                                "Artifact Slot": slot,
                                "Main Stat": stat,
                                "Substat": substat_name,
                                "Substat Rank": substat_rank
                            })

# Convert enhanced data v2 to DataFrame, write to (pipe delimited) CSV file
df_enhanced_v2 = pd.DataFrame(enhanced_data_v2)
df_enhanced_v2.to_csv("output.csv", index=False, sep='|')

# Write summary info to txt file for human review
with open('summary.txt', 'w', encoding='utf-8') as file:
    df_enhanced_v2.info(buf=file)
    file.write('\n\n')

    file.write('UNIQUE CHARACTERS\n')
    character_lines = pd.DataFrame(sorted(df_enhanced_v2['Character'].value_counts().items()), columns=['Name', 'Count'])
    file.write(character_lines.to_string(index=False) + '\n\n')

    file.write('UNIQUE ARTIFACT SETS\n')
    artifact_sets_lines = pd.DataFrame(sorted(df_enhanced_v2['Artifact Set'].value_counts().items()), columns=['Name', 'Count'])
    file.write(artifact_sets_lines.to_string(index=False) + '\n\n')

    file.write('UNIQUE ARTIFACT SLOTS\n')
    artifact_slots = pd.DataFrame(sorted(df_enhanced_v2['Artifact Slot'].value_counts().items()), columns=['Name', 'Count'])
    file.write(artifact_slots.to_string(index=False) + '\n\n')

    file.write('UNIQUE MAIN STATS\n')
    main_stat_lines = pd.DataFrame(sorted(df_enhanced_v2['Main Stat'].value_counts().items()), columns=['Name', 'Count'])
    file.write(main_stat_lines.to_string(index=False) + '\n\n')

    file.write('UNIQUE SUBSTATS\n')
    substat_lines = pd.DataFrame(sorted(df_enhanced_v2['Substat'].value_counts().items()), columns=['Name', 'Count'])
    file.write(substat_lines.to_string(index=False) + '\n')