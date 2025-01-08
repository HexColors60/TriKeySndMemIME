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
                
                # 提取當前已存在的數字
                existing_numbers = {num for num, _ in key2ph[key1]}
                
                # 如果 num1 是 -1，選擇下一個未使用的數字
                if num1 == -1:
                    num1 = 1  # 從 1 開始
                    while num1 in existing_numbers:
                        num1 += 1

                # 添加新項目
                key2ph[key1].append((num1, words))

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
    pos = 0
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
            print(f"\rBuffer: {buffer}", end='', flush=True)  # Refresh the prompt
            continue

        if char == ' ':
            # Split the buffer into English + number pairs
            pairs = re.findall(r'([a-zA-Z]+)(\d+)?', buffer)
            
            for pair in pairs:
                english, num_str = pair
                num = int(num_str) if num_str else 1  # Default to 1 if no number is provided

                # 查找 key2ph 中的對應鍵值
                if english in key2ph:
                    # 檢查 num 是否匹配 key2ph 中的第一個數字
                    matched_phrase = next(
                        (phrase_list for number, phrase_list in key2ph[english] if number == num),
                        None
                    )
                    if matched_phrase:
                        # 將對應的短語加入到 output_buffer
                        output_buffer += ''.join(matched_phrase)
                    
            print(f"\nOutput: {output_buffer}")
            
            # Reset the buffers and position counters
            buffer = ''
            output_buffer = ''
            num = 0
            continue

        if char.isdigit():
            # Handle multi-digit number
            num = num * 10 + int(char)
            buffer += char
            pos = len(buffer)
            continue

        if ord(char) in (8, 127):  # Backspace key
            if buffer:
                buffer = buffer[:-1]  # Remove the last character from the buffer
                pos = min(pos, len(buffer))  # Adjust pos if necessary
                print(f"\rBuffer: {buffer}", end='', flush=True)  # Refresh the prompt
            continue

        buffer += char
        num = 0  # Reset number on non-digit input

        if buffer[pos:] in key2ph:
            options = key2ph[buffer[pos:]]
            print("\nOptions:")
            for idx, (number, option) in enumerate(options, start=1):
                # 確保顯示的序號與 key2ph 中的數字一致
                print(f"{number}: {''.join(option)}")
            print(f"\rBuffer: {buffer}", end='', flush=True)  # 刷新提示符

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
