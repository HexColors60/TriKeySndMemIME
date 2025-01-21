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

def paginate(data, lines_per_page=25):
    """分頁顯示內容，每頁顯示指定行數。"""
    for i in range(0, len(data), lines_per_page):
        for line in data[i:i + lines_per_page]:
            print(line)
        if i + lines_per_page < len(data):
            print("--- 按空白鍵繼續，或 q 結束 ---\n", end="", flush=True)
            while True:
                char = getch()
                if char == ' ':
                    break
                elif char == 'q':
                    print("\nExiting pagination.")
                    return

def parse_mem_file(file_name):
    """解析 tmp_tksm_words.txt 檔案為 mem2char 格式。

    格式:
    每行由索引（兩個小寫字母）和26個Unicode字符組成，例如：
    aa ﹏﹏﹏黯﹏﹏暗﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏
    """
    mem2char = {}
    with open(file_name, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("##"):  # 跳過註解行和空行
                continue

            # 匹配索引和26個字符
            match = re.match(r'^([a-z]{2})\s+(.{26})$', line)
            if match:
                index = match[1]  # 索引（例如 'aa', 'ab'）
                data = list(match[2])  # 26個Unicode字符
                mem2char[index] = data
            else:
                print(f"Invalid line format: {line}")
    return mem2char

def parse_word_file(file_name, word2pinyin, key2ph):
    """解析單詞檔案，建立 key2ph 結構，用於查詢詞組與鍵位關聯。"""
    def unescape_string(s):
        """將轉義字符轉換為對應的實際字符"""
        return s.replace(r'\"', '"').replace(r'\t', '\t').replace(r'\n', '\n')

    with open(file_name, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()  # 去除行首尾的空白
            if not line:  # 跳過空行
                continue

            # 判斷是否是以引號開頭的字符串
            if line.startswith('"'):
                # 找到結束的引號位置，處理轉義字符
                match = re.match(r'"(.*?)"\s*(.*)', line)
                if not match:
                    print(f"Invalid format in line: {line}")
                    continue

                # 提取詞組和剩餘內容
                raw_words, rest = match.groups()
                words = [unescape_string(raw_words)]  # 將轉義字符解析為正常字符串
            else:
                # 傳統模式處理
                parts = re.split(r'[\s\t]+', line, maxsplit=1)
                words = [parts[0]]  # 第一部分是詞組，視為整體
                rest = parts[1] if len(parts) > 1 else ''

            num1 = -1  # 預設索引值
            key1 = None

            # 檢查剩餘內容是否包含 key/number
            if rest.isdigit():
                num1 = int(rest)
            elif re.match(r'^[a-zA-Z]+\d*$', rest):
                match = re.match(r'^([a-zA-Z]+)(\d*)$', rest)
                if match:
                    key1 = match[1]
                    if match[2]:
                        num1 = int(match[2])

            # 如果 key1 為空，根據詞組生成 key1，默認為 'v'
            if not key1:
                key1_parts = [word2pinyin.get(char, '') for word in words for char in word]
                key1 = ''.join(key1_parts) if any(key1_parts) else 'v'  # 如果沒有拼音，僅使用單一的 'v'

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
    """解析 .cin 檔案，建立 word2pinyin 結構。"""
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
                    english = match[1]  # 英文字母鍵
                    character = match[2][0]  # 對應的漢字
                    if character not in word2pinyin:
                        word2pinyin[character] = english[0] if english else ''
    return word2pinyin

def input_loop(key2ph, mem2char):
    """用戶輸入循環，支持即時查詢 key2ph 和 mem2char 結構。"""
    print("Enter input mode (Ctrl-C or Ctrl-D to exit):")
    buffer = ''
    output_buffer = ''
    num = 0
    pos = 0
    while True:
        try:
            char = getch()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if ord(char) in (3, 4):  # Ctrl-C (3) or Ctrl-D (4)
            print("\nExiting.")
            break

        print(char, end='', flush=True)

        if char == '~':
            print("\nKey2Ph Table:")
            output = [f"{key}: {phrases}" for key, phrases in key2ph.items()]
            paginate(output)
            print(f"\rBuffer: {buffer}", end='', flush=True)
            continue
            
        if char == ' ':
            # Split the buffer into English + number pairs
            pairs = re.findall(r'([a-zA-Z]+)(\d+)?', buffer)

            for pair in pairs:
                english, num_str = pair
                num = int(num_str) if num_str else 1  # Default to 1 if no number is provided

                # 查找 key2ph 中的對應鍵值
                if english in key2ph:
                    matched_phrase = next(
                        (phrase_list for number, phrase_list in key2ph[english] if number == num),
                        None
                    )
                    if matched_phrase:
                        output_buffer += ''.join(matched_phrase)

                # 當沒有提供數字時，處理 raw_chars
                if not num_str:
                    raw_chars = english
                    groups = [raw_chars[i:i+3] for i in range(0, len(raw_chars), 3)]
                    left_chars = ''
                    for group in groups:
                        if len(group) == 3:
                            key = group[:2]  # Extract the first two characters as the key
                            index = ord(group[2]) - ord('a')  # Convert the third character to an index (0-25)
                            if key in mem2char and 0 <= index < len(mem2char[key]):
                                output_buffer += mem2char[key][index]
                        else:
                            left_chars += group
                    
                    # 嘗試在 key2ph 中匹配剩餘字符
                    if left_chars in key2ph:
                        for _, words in key2ph[left_chars]:
                            output_buffer += ''.join(words)

            print(f"\nOutput: {output_buffer}")
            buffer = ''
            output_buffer = ''
            num = 0
            pos = 0
            continue

        if char.isdigit():
            num = num * 10 + int(char)
            buffer += char
            pos = len(buffer)
            continue

        if ord(char) in (8, 127):  # Backspace key
            if buffer:
                buffer = buffer[:-1]
                pos = min(pos, len(buffer))
                print(f"\rBuffer: {buffer}", end='', flush=True)
            continue

        buffer += char
        num = 0

        if buffer[pos:] in key2ph:
            options = key2ph[buffer[pos:]]
            print("\nOptions:")
            for idx, (number, option) in enumerate(options, start=1):
                print(f"{number}: {''.join(option)}")
            print(f"\rBuffer: {buffer}", end='', flush=True)

        if len(buffer[pos:]) == 2:
            print("\n## ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ")
            if buffer[pos:] in mem2char:
                print(f"{buffer[pos:]} {''.join(mem2char[buffer[pos:]])}")
            print(f"\rBuffer: {buffer}", end='', flush=True) 

if __name__ == "__main__":
    cin_file = 'pinyin.cin'
    if not os.path.exists(cin_file):
        print(f"Error: {cin_file} not found.")
        exit(1)

    word2pinyin = parse_cin_file(cin_file)
    key2ph = {}
    for file_name in os.listdir():
        if re.match(r'word.*\.txt$', file_name):
            parse_word_file(file_name, word2pinyin, key2ph)

    mem_file = 'tmp_tksm_words.txt'
    if os.path.exists(mem_file):
        mem2char = parse_mem_file(mem_file)
        print("Parsed mem2char data loaded.")
    else:
        mem2char = {}

    input_loop(key2ph, mem2char)
