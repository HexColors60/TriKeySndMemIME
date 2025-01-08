import os
import re
import sys
import termios
import tty

def getch():
    """Reads a single character from standard input without requiring Enter."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        char = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return char

def parse_word_file(file_name, word2pinyin, key2ph):
    with open(file_name, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()  # 去除行首尾的空白
            if not line:  # 跳過空行
                continue

            # 分割行內容
            parts = re.split(r'[\s\t]+', line, maxsplit=1)

            words = [parts[0]]  # 第一部分是詞組，視為整體
            rest = parts[1] if len(parts) > 1 else ''  # 如果有剩餘內容則處理

            num1 = -1  # 預設索引值
            key1 = None

            # 檢查剩餘內容
            if rest.isdigit():
                num1 = int(rest)
            elif re.match(r'^[a-zA-Z]+\d*$', rest):
                match = re.match(r'^([a-zA-Z]+)(\d*)$', rest)
                if match:
                    key1 = match[1]
                    if match[2]:
                        num1 = int(match[2])

            # 如果 key1 為空，根據詞組生成 key1
            if not key1:
                key1 = ''.join(word2pinyin.get(char, '') for word in words for char in word)

            # 構建 key2ph
            if key1:
                if key1 not in key2ph:
                    key2ph[key1] = []
                key2ph[key1].append((num1 if num1 != -1 else len(key2ph[key1]) + 1, words))

def parse_cin_file(cin_file):
    word2pinyin = {}
    with open(cin_file, 'r', encoding='utf-8') as file:
        in_chardef = False
        for line in file:
            line = line.strip()
            if line == "%chardef begin":
                in_chardef = True
                continue
            if line == "%chardef end":
                break

            if in_chardef:
                match = re.match(r'^([a-zA-Z]*\d*)\s+([\u4e00-\u9fff]+):?.*$', line)
                if match:
                    english = match[1]
                    character = match[2][0]
                    if character not in word2pinyin:
                        word2pinyin[character] = english[0] if english else ''
    return word2pinyin

def input_loop(key2ph):
    print("Enter input mode (Ctrl-C or Ctrl-D to exit):")
    buffer = ''
    output_buffer = ''
    num = 0  # To track multi-digit input
    while True:
        try:
            char = getch()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if ord(char) == 3 or ord(char) == 4:  # Check for Ctrl-C (3) or Ctrl-D (4)
            print("\nExiting.")
            break

        print(char, end='', flush=True)  # Echo the input character immediately

        if char == '~':
            print("\nKey2Ph Table:")
            for key, phrases in key2ph.items():
                print(f"{key}: {phrases}")
            continue

        if char == ' ':
            # On space, process the output
            if buffer in key2ph and 1 <= num <= len(key2ph[buffer]):
                output_buffer += ''.join(key2ph[buffer][num - 1][1])
            print(f"\nOutput: {output_buffer}")
            buffer = ''
            output_buffer = ''
            num = 0
            continue

        if char.isdigit():
            # Handle multi-digit number
            num = num * 10 + int(char)
            continue

        buffer += char
        num = 0  # Reset number on non-digit input

        if buffer in key2ph:
            options = key2ph[buffer]
            print("\nOptions:")
            for idx, (_, option) in enumerate(options, start=1):
                print(f"{idx}: {''.join(option)}")

if __name__ == "__main__":
    # Specify your .cin file path here
    cin_file = 'pinyin.cin'
    if not os.path.exists(cin_file):
        print(f"Error: {cin_file} not found.")
        exit(1)

    word2pinyin = parse_cin_file(cin_file)
    key2ph = {}
    for file_name in os.listdir():
        if re.match(r'word.*\.txt$', file_name):
            parse_word_file(file_name, word2pinyin, key2ph)

    input_loop(key2ph)
