import json
import os
import pandas as pd
import re
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

API_KEY = os.environ['GOOGLE_API_KEY']
SPREADSHEET_ID = '1gNxZ2xab1J6o1TuNVWMeLOZ7TPOqrsf3SshP5DLvKzI'

# Validation counters for summary
validation_counts = {
    'rows_fetched': 0,
    'rows_after_header_trim': 0,
    'rows_filtered_keywords': 0,
    'rows_after_keyword_filter': 0,
    'rows_missing_data': 0,
    'rows_with_meaningful_data': 0,
    'artifact_lines_no_rank': 0,
    'main_stat_lines_no_slot': 0,
    'substat_lines_no_rank': 0,
    'skipped_duplicate_main_substat': 0,
    'final_output_rows': 0,
}

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
    validation_counts['rows_fetched'] += len(df)

    # Rename TRAVELER rows in column 1
    df.iloc[:, 1] = df.iloc[:, 1].apply(
        lambda x: f"{elements[i]} TRAVELER" if isinstance(x, str) and x.startswith("TRAVELER") else x
    )

    # Trim the first 5 rows (0-indexed)
    df_trimmed = df.iloc[5:].reset_index(drop=True)
    validation_counts['rows_after_header_trim'] += len(df_trimmed)
    dfs.append(df_trimmed)

# Concatenate all the trimmed dataframes into one final dataframe
df_trimmed = pd.concat(dfs, ignore_index=True)

# Step 2: Filter out unwanted rows (e.g., "4 STAR", "5 STAR", "NOTES", and "Last Updated:" rows)
filter_keywords = ["4 STAR", "5 STAR", "NOTES", "*portrait \npending*"]

df_cleaned = df_trimmed[
    ~df_trimmed[1].isin(filter_keywords) &
    ~df_trimmed[1].astype(str).str.startswith("Last Updated:")
].reset_index(drop=True)
validation_counts['rows_filtered_keywords'] = len(df_trimmed) - len(df_cleaned)
validation_counts['rows_after_keyword_filter'] = len(df_cleaned)

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
validation_counts['rows_missing_data'] = len(df_parsed) - len(df_final_cleaned)
validation_counts['rows_with_meaningful_data'] = len(df_final_cleaned)

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
        # Formerly included " and " which is now in an artifact set name, alas
        ["~=", "|"],
        ["≈", "|"],
        ["(2) [Choose One] and", "|"],  # number parentheticals (and other dirt) sometimes act as separators
        ["(2) and", "|"],
        ["(2)", "|"],
        ["(4)", "|"],

        # Remove garbage
        ["[Choose One]", ""],  
        ["[Choose Two]", ""],
        ["[Choose two]", ""],
        ["[see notes]", ""],
        ["Mixes of", ""],
        ["Furina teams only, performs as well or better than Nighttime Whispers in the Echoing Woods", ""],
        ["Other damaging options (see DPS)", ""],
        ["*", ""],
        ["(Crit Rate secondary stat weapon only)", ""],

        # Canonicalize names
        ["15% Anemo DMG Set", "15% Anemo DMG set"],
        ["15% Healing Bonus", "15% Healing Bonus set"],
        ["15% Healing Bonus set set", "15% Healing Bonus set"],  # alas
        ["15% Hydro DMG Bonus set", "15% Hydro DMG set"],
        ["18 ATK% set", "18% ATK set"],
        ["18% ATK Set", "18% ATK set"],
        ["20% ER Set", "20% Energy Recharge set"],
        ["20% ER set", "20% Energy Recharge set"],
        ["20% HP", "20% HP set"],
        ["20% HP set set", "20% HP set"],  # alas again
        ["80 EM", "80 EM set"],
        ["80 EM set set", "80 EM set"],  # alas again again
        ["Emblem Of Severed Fate", "Emblem of Severed Fate"],
        ["Marechausse Hunter", "Marechaussee Hunter"],
        ["Ocean Hued Clam", "Ocean-Hued Clam"],
        ["Desert Pavillion Chronicle", "Desert Pavilion Chronicle"],
        ["Silken Moon Serenade", "Silken Moon's Serenade"],

        # Set category expansions; assume only 5 star sets matter
        ["15% Anemo DMG set", "15% Anemo DMG set|Viridescent Venerer|Desert Pavilion Chronicle"],
        ["15% Cryo DMG set", "15% Cryo DMG set|Blizzard Strayer|Finale of the Deep Galleries"],
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
            validation_counts['artifact_lines_no_rank'] += 1
            continue
        artifact_set_names = clean_and_split_artifact_set_names(artifact_set_names_text)
        for artifact_set_name in artifact_set_names:
            for main_stat_line in main_stat_lines:
                # Split main stats by slashes and clean
                slot_stat_parts = main_stat_line.split(" - ")
                slot = slot_stat_parts[0].strip() if len(slot_stat_parts) > 1 else None
                if slot is None:
                    validation_counts['main_stat_lines_no_slot'] += 1
                    continue
                main_stats = clean_and_split_stats(slot_stat_parts[1]) if len(slot_stat_parts) > 1 else []
                for stat in main_stats:
                    for substat_line in substat_lines:
                        substat_rank, substat_text = extract_rank(substat_line)
                        if substat_rank is None:
                            validation_counts['substat_lines_no_rank'] += 1
                            continue
                        substat_names = clean_and_split_stats(substat_text)
                        for substat_name in substat_names:
                            if stat == substat_name:
                                validation_counts['skipped_duplicate_main_substat'] += 1
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
validation_counts['final_output_rows'] = len(df_enhanced_v2)
os.makedirs("output", exist_ok=True)
df_enhanced_v2.to_csv("output/output.csv", index=False, sep='|')


def generate_web_json(df):
    """Generate optimized JSON for the web artifact evaluator."""
    # Build meta information
    sets = sorted(df['Artifact Set'].unique().tolist())
    slots = sorted(df['Artifact Slot'].unique().tolist())
    characters = sorted(df['Character'].unique().tolist())
    substats = sorted(df['Substat'].unique().tolist())

    # Main stats per slot
    main_stats_by_slot = {}
    for slot in slots:
        main_stats_by_slot[slot] = sorted(
            df[df['Artifact Slot'] == slot]['Main Stat'].unique().tolist()
        )

    meta = {
        'sets': sets,
        'slots': slots,
        'characters': characters,
        'substats': substats,
        'mainStatsBySlot': main_stats_by_slot
    }

    # Build bySet index: set → characters + slot breakdowns
    by_set = {}
    for artifact_set in sets:
        set_df = df[df['Artifact Set'] == artifact_set]

        # Get unique character/role combinations for this set
        char_roles = set_df.groupby(['Character', 'Role', 'Preferred Role', 'Artifact Set Rank']).size().reset_index()
        characters_list = []
        seen_char_roles = set()
        for _, row in char_roles.iterrows():
            key = (row['Character'], row['Role'])
            if key not in seen_char_roles:
                seen_char_roles.add(key)
                characters_list.append({
                    'character': row['Character'],
                    'role': row['Role'],
                    'preferred': bool(row['Preferred Role']),
                    'setRank': int(row['Artifact Set Rank'])
                })

        # Sort by setRank, then character name
        characters_list.sort(key=lambda x: (x['setRank'], x['character']))

        # Build slot breakdown
        slot_breakdown = {}
        for slot in slots:
            slot_df = set_df[set_df['Artifact Slot'] == slot]
            if slot_df.empty:
                continue

            # Main stats for this slot
            main_stat_data = {}
            for main_stat in slot_df['Main Stat'].unique():
                ms_df = slot_df[slot_df['Main Stat'] == main_stat]

                # Characters wanting this main stat
                ms_chars = ms_df.groupby(['Character', 'Role', 'Preferred Role', 'Artifact Set Rank']).size().reset_index()
                ms_char_list = []
                seen = set()
                for _, row in ms_chars.iterrows():
                    key = (row['Character'], row['Role'])
                    if key not in seen:
                        seen.add(key)
                        ms_char_list.append({
                            'character': row['Character'],
                            'role': row['Role'],
                            'preferred': bool(row['Preferred Role']),
                            'setRank': int(row['Artifact Set Rank'])
                        })
                ms_char_list.sort(key=lambda x: (x['setRank'], x['character']))

                # Substats for this main stat - include character+role pairs
                substat_data = ms_df.groupby(['Substat', 'Substat Rank']).apply(
                    lambda g: g[['Character', 'Role']].drop_duplicates().to_dict('records')
                ).reset_index(name='char_roles')
                substats_list = []
                for _, row in substat_data.iterrows():
                    char_roles = [{'character': cr['Character'], 'role': cr['Role']}
                                  for cr in row['char_roles']]
                    char_roles.sort(key=lambda x: (x['character'], x['role']))
                    substats_list.append({
                        'substat': row['Substat'],
                        'rank': int(row['Substat Rank']),
                        'characterRoles': char_roles
                    })
                substats_list.sort(key=lambda x: (x['rank'], x['substat']))

                main_stat_data[main_stat] = {
                    'characters': ms_char_list,
                    'substats': substats_list
                }

            slot_breakdown[slot] = main_stat_data

        # Build combined fixed-main-stat slot for Flower/Feather.
        # Source data does not encode these slots explicitly; aggregate by set.
        fixed_char_data = set_df.groupby(
            ['Character', 'Role', 'Preferred Role', 'Artifact Set Rank']
        ).size().reset_index()
        fixed_char_list = []
        fixed_seen = set()
        for _, row in fixed_char_data.iterrows():
            key = (row['Character'], row['Role'])
            if key not in fixed_seen:
                fixed_seen.add(key)
                fixed_char_list.append({
                    'character': row['Character'],
                    'role': row['Role'],
                    'preferred': bool(row['Preferred Role']),
                    'setRank': int(row['Artifact Set Rank'])
                })
        fixed_char_list.sort(key=lambda x: (x['setRank'], x['character']))

        fixed_sub_data = set_df.groupby(['Substat', 'Substat Rank']).apply(
            lambda g: g[['Character', 'Role']].drop_duplicates().to_dict('records')
        ).reset_index(name='char_roles')
        fixed_sub_list = []
        for _, row in fixed_sub_data.iterrows():
            char_roles = [{'character': cr['Character'], 'role': cr['Role']}
                          for cr in row['char_roles']]
            char_roles.sort(key=lambda x: (x['character'], x['role']))
            fixed_sub_list.append({
                'substat': row['Substat'],
                'rank': int(row['Substat Rank']),
                'characterRoles': char_roles
            })
        fixed_sub_list.sort(key=lambda x: (x['rank'], x['substat']))

        by_set[artifact_set] = {
            'characters': characters_list,
            'slots': slot_breakdown,
            'fixedSlots': {
                'slot': 'Flower/Feather',
                'mainStatLabel': 'Fixed Main Stats (HP / ATK)',
                'characters': fixed_char_list,
                'substats': fixed_sub_list
            }
        }

    # Build byArtifact index: "set|slot|mainStat" → characters + substats
    by_artifact = {}
    for artifact_set in sets:
        set_df = df[df['Artifact Set'] == artifact_set]
        for slot in slots:
            slot_df = set_df[set_df['Artifact Slot'] == slot]
            for main_stat in slot_df['Main Stat'].unique():
                key = f"{artifact_set}|{slot}|{main_stat}"
                ms_df = slot_df[slot_df['Main Stat'] == main_stat]

                # Characters
                char_data = ms_df.groupby(['Character', 'Role', 'Preferred Role', 'Artifact Set Rank']).size().reset_index()
                char_list = []
                seen = set()
                for _, row in char_data.iterrows():
                    k = (row['Character'], row['Role'])
                    if k not in seen:
                        seen.add(k)
                        char_list.append({
                            'character': row['Character'],
                            'role': row['Role'],
                            'preferred': bool(row['Preferred Role']),
                            'setRank': int(row['Artifact Set Rank'])
                        })
                char_list.sort(key=lambda x: (x['setRank'], x['character']))

                # Substats with character+role attribution
                sub_data = ms_df.groupby(['Substat', 'Substat Rank']).apply(
                    lambda g: g[['Character', 'Role']].drop_duplicates().to_dict('records')
                ).reset_index(name='char_roles')
                sub_list = []
                for _, row in sub_data.iterrows():
                    char_roles = [{'character': cr['Character'], 'role': cr['Role']}
                                  for cr in row['char_roles']]
                    char_roles.sort(key=lambda x: (x['character'], x['role']))
                    sub_list.append({
                        'substat': row['Substat'],
                        'rank': int(row['Substat Rank']),
                        'characterRoles': char_roles
                    })
                sub_list.sort(key=lambda x: (x['rank'], x['substat']))

                by_artifact[key] = {
                    'characters': char_list,
                    'substats': sub_list
                }

    # Build byMainStat index: "slot|mainStat" (ignores set) → characters + substats
    by_main_stat = {}
    for slot in slots:
        slot_df = df[df['Artifact Slot'] == slot]
        for main_stat in slot_df['Main Stat'].unique():
            key = f"{slot}|{main_stat}"
            ms_df = slot_df[slot_df['Main Stat'] == main_stat]

            # Characters with best (lowest) set rank for this slot/main stat across all sets.
            char_data = ms_df.groupby(
                ['Character', 'Role', 'Preferred Role']
            )['Artifact Set Rank'].min().reset_index(name='Best Set Rank')
            char_list = []
            for _, row in char_data.iterrows():
                char_list.append({
                    'character': row['Character'],
                    'role': row['Role'],
                    'preferred': bool(row['Preferred Role']),
                    'setRank': int(row['Best Set Rank'])
                })
            char_list.sort(key=lambda x: (x['setRank'], x['character']))

            # Substats with best rank per character+role+substat, then grouped for UI display.
            best_sub_per_char = ms_df.groupby(
                ['Character', 'Role', 'Substat']
            )['Substat Rank'].min().reset_index(name='Best Substat Rank')
            sub_data = best_sub_per_char.groupby(['Substat', 'Best Substat Rank']).apply(
                lambda g: g[['Character', 'Role']].drop_duplicates().to_dict('records')
            ).reset_index(name='char_roles')
            sub_list = []
            for _, row in sub_data.iterrows():
                char_roles = [{'character': cr['Character'], 'role': cr['Role']}
                              for cr in row['char_roles']]
                char_roles.sort(key=lambda x: (x['character'], x['role']))
                sub_list.append({
                    'substat': row['Substat'],
                    'rank': int(row['Best Substat Rank']),
                    'characterRoles': char_roles
                })
            sub_list.sort(key=lambda x: (x['rank'], x['substat']))

            by_main_stat[key] = {
                'characters': char_list,
                'substats': sub_list
            }

    return {
        'meta': meta,
        'bySet': by_set,
        'byArtifact': by_artifact,
        'byMainStat': by_main_stat
    }


# Generate and write JSON for web evaluator
web_json = generate_web_json(df_enhanced_v2)
with open('output/artifact_data.json', 'w', encoding='utf-8') as f:
    json.dump(web_json, f, separators=(',', ':'))

# Generate HTML from template
with open('artifact_evaluator_template.html', 'r', encoding='utf-8') as f:
    html_template = f.read()
json_str = json.dumps(web_json, separators=(',', ':'))
html_output = html_template.replace('ARTIFACT_DATA_PLACEHOLDER', json_str)
with open('output/artifact_evaluator.html', 'w', encoding='utf-8') as f:
    f.write(html_output)


# Helper functions for summary analysis
def find_low_frequency_values(series, threshold=2):
    """Find values that appear <= threshold times (potential typos/uncanonicalized)."""
    counts = series.value_counts()
    return counts[counts <= threshold].sort_values()


# Canonical artifact set category names that intentionally contain percentages
ARTIFACT_SET_CATEGORIES = {
    "15% Anemo DMG set",
    "15% Cryo DMG set",
    "15% Healing Bonus set",
    "15% Hydro DMG set",
    "18% ATK set",
    "20% Energy Recharge set",
    "20% HP set",
    "25% Physical DMG set",
    "80 EM set",
}


def find_suspicious_strings(series, allowed_percentages=None):
    """Find values containing patterns that suggest incomplete cleanup."""
    if allowed_percentages is None:
        allowed_percentages = set()
    suspicious_patterns = [
        (r'[~≈]', 'contains ~ or ≈'),
        (r'[\[\]]', 'contains brackets []'),
        (r'\*', 'contains asterisk'),
        (r'\d+%', 'contains percentage (may need expansion)'),
        (r'.{50,}', 'very long string (>50 chars)'),
    ]
    results = []
    for value in series.unique():
        if not isinstance(value, str):
            continue
        for pattern, reason in suspicious_patterns:
            if re.search(pattern, value):
                # Skip percentage check for known canonical category names
                if 'percentage' in reason and value in allowed_percentages:
                    continue
                results.append((value, reason))
                break  # Only report first matching reason per value
    return results

# Write summary info to txt file for human review
with open('output/summary.txt', 'w', encoding='utf-8') as file:
    # Section: Validation Counts (E)
    file.write('=' * 60 + '\n')
    file.write('VALIDATION COUNTS\n')
    file.write('=' * 60 + '\n')
    file.write(f"Rows fetched from API:          {validation_counts['rows_fetched']}\n")
    file.write(f"Rows after header trim:         {validation_counts['rows_after_header_trim']}\n")
    file.write(f"Rows filtered (keywords):       {validation_counts['rows_filtered_keywords']}\n")
    file.write(f"Rows after keyword filter:      {validation_counts['rows_after_keyword_filter']}\n")
    file.write(f"Rows missing data:              {validation_counts['rows_missing_data']}\n")
    file.write(f"Rows with meaningful data:      {validation_counts['rows_with_meaningful_data']}\n")
    file.write(f"Artifact lines without rank:    {validation_counts['artifact_lines_no_rank']}\n")
    file.write(f"Main stat lines without slot:   {validation_counts['main_stat_lines_no_slot']}\n")
    file.write(f"Substat lines without rank:     {validation_counts['substat_lines_no_rank']}\n")
    file.write(f"Skipped (main=substat):         {validation_counts['skipped_duplicate_main_substat']}\n")
    file.write(f"Final output rows:              {validation_counts['final_output_rows']}\n")
    file.write('\n')

    # Section: Suspicious Strings (B)
    file.write('=' * 60 + '\n')
    file.write('SUSPICIOUS STRINGS (may need cleanup)\n')
    file.write('=' * 60 + '\n')
    suspicious_found = False
    for col_name, col_label in [('Artifact Set', 'Artifact Sets'),
                                 ('Main Stat', 'Main Stats'),
                                 ('Substat', 'Substats'),
                                 ('Character', 'Characters'),
                                 ('Role', 'Roles')]:
        # Exclude known canonical artifact set categories from percentage check
        allowed = ARTIFACT_SET_CATEGORIES if col_name == 'Artifact Set' else None
        suspicious = find_suspicious_strings(df_enhanced_v2[col_name], allowed)
        if suspicious:
            suspicious_found = True
            file.write(f"\n{col_label}:\n")
            for value, reason in suspicious:
                file.write(f"  - \"{value}\" ({reason})\n")
    if not suspicious_found:
        file.write("None found.\n")
    file.write('\n')

    # Section: Low Frequency Values (A)
    file.write('=' * 60 + '\n')
    file.write('LOW FREQUENCY VALUES (count <= 2, may be typos)\n')
    file.write('=' * 60 + '\n')
    low_freq_found = False
    for col_name, col_label in [('Artifact Set', 'Artifact Sets'),
                                 ('Main Stat', 'Main Stats'),
                                 ('Substat', 'Substats')]:
        low_freq = find_low_frequency_values(df_enhanced_v2[col_name])
        if len(low_freq) > 0:
            low_freq_found = True
            file.write(f"\n{col_label}:\n")
            for value, count in low_freq.items():
                file.write(f"  - \"{value}\" (count: {count})\n")
    if not low_freq_found:
        file.write("None found.\n")
    file.write('\n')

    # Section: DataFrame info
    file.write('=' * 60 + '\n')
    file.write('DATAFRAME INFO\n')
    file.write('=' * 60 + '\n')
    df_enhanced_v2.info(buf=file)
    file.write('\n\n')

    # Section: Unique value counts
    file.write('=' * 60 + '\n')
    file.write('UNIQUE VALUE COUNTS\n')
    file.write('=' * 60 + '\n\n')

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
