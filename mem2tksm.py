import re
import glob

# Define constants
KEYORDER = "abcdefghijklmnopqrstuvwxyz"
PINYIN_CIN = "pinyin.cin"
OUTPUT_FILE = "tmp_tksm_words.txt"
DEBUG = True  # Debug flag

# Load data from pinyin.cin
def load_cin(filename):
    pinyin_map = {}
    with open(filename, encoding='utf-8') as file:
        in_chardef = False
        for line in file:
            line = line.strip()
            if line == "%chardef begin":
                in_chardef = True
                continue
            if line == "%chardef end":
                break
            if in_chardef:
                match = re.match(r"(\w+)\s+(.+)", line)
                if match:
                    key, chars = match.groups()
                    for char in chars:
                        if char not in pinyin_map:
                            pinyin_map[char] = []
                        pinyin_map[char].append(key[0])  # Keep the first letter of the pinyin
    return pinyin_map

# Initialize unused table
def initialize_unused_table():
    return {
        (key1, key2): list(KEYORDER) for key1 in KEYORDER for key2 in KEYORDER
    }

# Load data from mem*.txt
def load_mem_txt(unused_table):
    words_map = {}

    for filename in glob.glob("mem*.txt"):
        current_keyword = None
        with open(filename, encoding='utf-8') as file:
            for line in file:
                line = line.rstrip()
                if line.startswith("(") and line.endswith(")"):
                    continue  # Ignore comments
                if not line.startswith(" "):
                    current_keyword = line.strip()
                    continue
                if current_keyword:
                    if line.startswith("  "):  # Two spaces, process individual characters with <...>
                        chars = line.strip()
                        for match in re.finditer(r"(\S)(?:<([^>]+)>)?", chars):
                            char = match.group(1)
                            third_code = match.group(2)

                            # Determine parent_code
                            parent_code = current_keyword[0]
                            second_code = current_keyword[1]

                            # If no <...>, auto-assign from KEYORDER for (first_code, second_code)
                            if not third_code:
                                base_key = (parent_code, second_code)
                                if base_key in unused_table and unused_table[base_key]:
                                    third_code = unused_table[base_key].pop(0)
                                else:
                                    print(f"Error: No available third_code for base '{base_key}'.")

                            if char not in words_map:
                                words_map[char] = {
                                    'parent_code': parent_code,
                                    'third_code': third_code
                                }
                            else:
                                print(f"Conflict detected for '{char}' at code '{third_code}'")
                    elif line.startswith(" "):  # One space, process two-letter codes
                        chars = line.strip()
                        for char in chars:
                            if char not in words_map:
                                words_map[char] = {
                                    'parent_code': current_keyword[0],
                                    'third_code': current_keyword[1]
                                }
                            else:
                                print(f"Conflict detected for '{char}' at code '{current_keyword[:2]}'")
    return words_map

# Generate tmp_tksm_words.txt
def generate_tksm_words(pinyin_map, words_map):
    used_codes = {}
    output_lines = ["## ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"]

    for char, data in words_map.items():
        parent_code = data['parent_code']
        third_code = data.get('third_code')
        code1 = pinyin_map[char][0] if char in pinyin_map else "?"  # First Pinyin character

        base_code = code1 + parent_code

        if third_code:
            position_index = KEYORDER.index(third_code)
            if base_code not in used_codes:
                used_codes[base_code] = ["﹏"] * 26
            if used_codes[base_code][position_index] == "﹏":
                used_codes[base_code][position_index] = char
            else:
                print(f"Conflict: '{char}' conflicts at position {position_index} in code '{base_code}'")
        else:
            # Fill in the next available position
            if base_code not in used_codes:
                used_codes[base_code] = ["﹏"] * 26
            for i, slot in enumerate(used_codes[base_code]):
                if slot == "﹏":
                    used_codes[base_code][i] = char
                    break

    # Fill unused codes with placeholders
    for key1 in KEYORDER:
        for key2 in KEYORDER:
            base_code = key1 + key2
            if base_code not in used_codes:
                used_codes[base_code] = ["﹏"] * 26

            output_lines.append(
                f"{base_code} {''.join(used_codes[base_code])}"
            )

    return output_lines

# Main function
def main():
    pinyin_map = load_cin(PINYIN_CIN)
    unused_table = initialize_unused_table()
    words_map = load_mem_txt(unused_table)

    if DEBUG:
        print("Debug: Loaded pinyin_map:")
        for k, v in pinyin_map.items():
            print(f"{k}: {', '.join(v)}")
        print("Debug: Loaded words_map:")
        for k, v in words_map.items():
            print(f"{k}: {v}")

    output_lines = generate_tksm_words(pinyin_map, words_map)

    # Write output to file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        file.write("\n".join(output_lines))

    print(f"Output written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
