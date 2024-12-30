import re
import glob

# Define constants
KEYORDER = "abcdefghijklmnopqrstuvwxyz"
pinyin_cin = "pinyin.cin"
output_file = "tmp_tksm_words.txt"
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
                    key, char = match.groups()
                    if char not in pinyin_map:
                        pinyin_map[char] = []
                    pinyin_map[char].append(key[0])  # Only keep the first character of the pinyin
    return pinyin_map

# Load data from mem*.txt
def load_mem_txt():
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
                    if line.startswith("  "):  # Two spaces, get one code
                        chars = line.strip()
                        for char in chars:
                            if char not in words_map:
                                words_map[char] = current_keyword[0]
                            else:
                                print(f"Conflict detected for '{char}' at code '{current_keyword[0]}'")
                    elif line.startswith(" "):  # One space, get two codes
                        chars = line.strip()
                        for char in chars:
                            if char not in words_map:
                                words_map[char] = current_keyword[:2]
                            else:
                                print(f"Conflict detected for '{char}' at code '{current_keyword[:2]}'")
    return words_map

# Generate tmp_tksm_words.txt
def generate_tksm_words(pinyin_map, words_map):
    used_codes = {}
    output_lines = ["## ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"]

    for char in pinyin_map:
        if char in words_map:
            code1 = pinyin_map[char][0]  # First character from pinyin_map
            code2 = words_map[char][0]  # First character of words_map[char]
            code3 = words_map[char][1] if len(words_map[char]) > 1 else None  # Second character if exists

            base_code = code1 + code2

            if code3:
                position_index = KEYORDER.index(code3)
                if base_code not in used_codes:
                    used_codes[base_code] = ["﹏"] * 26
                if used_codes[base_code][position_index] == "﹏":
                    used_codes[base_code][position_index] = char
                else:
                    print(f"Conflict: '{char}' conflicts at position {position_index} in code '{base_code}'")
            else:
                # Find the first available position
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
    pinyin_map = load_cin(pinyin_cin)
    words_map = load_mem_txt()

    if DEBUG:
        print("Debug: Loaded pinyin_map:")
        for k, v in pinyin_map.items():
            print(f"{k}: {', '.join(v)}")
        print("Debug: Loaded words_map:")
        for k, v in words_map.items():
            print(f"{k}: {v}")

    output_lines = generate_tksm_words(pinyin_map, words_map)

    # Write output to file
    with open(output_file, "w", encoding="utf-8") as file:
        file.write("\n".join(output_lines))

    print(f"Output written to {output_file}")

if __name__ == "__main__":
    main()
