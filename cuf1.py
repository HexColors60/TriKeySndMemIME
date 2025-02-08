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

                # 查找是否已存在相同 key 和數字，但數據不同
                conflicting_entry = next((entry for entry in key2ph[key1] if entry[0] == num1 and entry[1] != words), None)
                if conflicting_entry:
                    # 更新舊條目並分配新數字
                    existing_numbers = {num for num, _ in key2ph[key1]}
                    new_num = 1
                    while new_num in existing_numbers:
                        new_num += 1
                    key2ph[key1].remove(conflicting_entry)
                    key2ph[key1].append((new_num, conflicting_entry[1]))
                    key2ph[key1].append((num1, words))
                    key2ph[key1].sort(key=lambda x: x[0])  # 按數字排序
                    continue

                # 查找是否已存在相同的詞組與鍵位
                existing_entry = next((entry for entry in key2ph[key1] if entry[1] == words), None)

                # 如果 num1 是 -1 且已有相同項目，則不添加新項目
                if num1 == -1:
                    if existing_entry:
                        continue
                    # 選擇下一個未使用的數字
                    existing_numbers = {num for num, _ in key2ph[key1]}
                    num1 = 1  # 從 1 開始
                    while num1 in existing_numbers:
                        num1 += 1

                # 如果存在相同的項目且 num1 不為 -1，替換數字
                elif existing_entry:
                    key2ph[key1].remove(existing_entry)
                    key2ph[key1].append((num1, words))
                    key2ph[key1].sort(key=lambda x: x[0])  # 按數字排序
                    continue

                # 添加新項目
                key2ph[key1].append((num1, words))
                key2ph[key1].sort(key=lambda x: x[0])  # 按數字排序

def parse_lime_file_old(cin_file):
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

def parse_lime_file(lime_file):
    """解析 .lime 檔案，建立 word2pinyin 結構。"""
    word2pinyin = {}
    keys2word = {}
    with open(lime_file, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) >= 2:
                key, word = parts[0], parts[1]
                if key not in keys2word:
                    keys2word[key] = [word]
                else:
                    keys2word[key].append(word)
            match = re.match(r'^([a-zA-Z]*\d*),([\u4e00-\u9fff]+):?.*$', line)
            if match:
                english = match[1]  # 英文字母鍵
                character = match[2][0]  # 對應的漢字
                if character not in word2pinyin:
                    word2pinyin[character] = english[0] if english else ''
    return word2pinyin, keys2word

import string

def xlen(text):
    """Calculate the display length of a string where non-ASCII, non-symbols count as 2."""
    symbols = set(string.punctuation + string.whitespace)
    return sum(2 if ord(c) > 127 or c not in symbols and not c.isascii() else 1 for c in text)

def format_options(options, width=80):
    grouped_options = {}

    # 將相同 key 的選項分組
    for idx, (key, option) in enumerate(options, start=1):
        if key not in grouped_options:
            grouped_options[key] = []
        grouped_options[key].append(f"{idx} {option}")

    lines = []
    
    for key in grouped_options:
        entries = grouped_options[key]
        current_line = f"{key}: "
        first = True  # 控制是否加 ", "

        for entry in entries:
            if xlen(current_line) + xlen(entry) + 2 <= width:  # +2 for ", "
                current_line += ("" if first else ", ") + entry
                first = False
            else:
                lines.append(current_line)
                current_line = f"{key}: {entry}"  # 開新行

        if current_line:
            lines.append(current_line)

    return "\n".join(lines)

# Example usage:
# print(format_options(options, width=80))

def input_loop(key2ph, mem2char, keys2word):
    hint_string_1 = """
ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ
ㄘㄅㄒㄉㄧㄈㄍㄏㄞㄐㄎㄌㄇㄋㄡㄆ　ㄖㄙㄊㄩㄑㄠㄨㄚㄗ
ㄟ　ㄕ　ㄝ　ㄜㄛ　ㄓㄤㄥㄢㄣ　　          ㄔ
　　  ˊ　 ˇ　　   ˋ 　ㄦ　　　      ˙　"""
    hint_string_2 = """
提示：許氏注音對應規則 第一類：字母對應 (1) 字音相似（發音類似）
- ㄅ → B, ㄆ → P, ㄇ → M, ㄈ → F, ㄉ → D, ㄊ → T, ㄋ → N, ㄌ → L
- ㄍ → G, ㄎ → K, ㄏ → H, ㄐ → J, ㄑ → Q, ㄒ → X, ㄖ → R, ㄗ → Z
- ㄘ → C, ㄙ → S, ㄝ → E, ㄞ → A, ㄟ → E, ㄡ → O, ㄣ → N, ㄧ → I

(2) 字形相似（形狀類似）
- ㄠ ← W (逆時針轉90度), ㄑ ← V (逆時針轉90度), ㄢ ← M (上下合併)
- ㄋ ← N (逆時針轉90度), ㄤ ← K (逆時針轉45度), ㄥ ← L (字形相似)
- ㄦ ← L (ㄦ右半邊與L相似), ㄚ ← Y (字形相似), ㄨ ← X (字形相似)
- ㄩ ← U (字形相似)

第二類：鍵盤排列記憶
- ㄗ → Z, ㄘ → C, ㄙ → S (依發音)
- ㄐ → J, ㄑ → Q, ㄒ → X (音標相似)
- ㄜ → G, ㄛ → H (手順方便)

【聲調鍵】- 一聲 → 空白鍵, 二聲 → D, 三聲 → F, 四聲 → J, 輕聲 → S """

    print(hint_string_2)
    print(hint_string_1)

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
            substring = buffer[pos:]
            print("\nKey2Ph Table:")
            matched_keys = [key for key in key2ph if key.startswith(substring)]
            if matched_keys:
                output = [f"{key}: {key2ph[key]}" for key in matched_keys]
            else:
                output = [f"{key}: {phrases}" for key, phrases in key2ph.items()]
            paginate(output)
            print(f"\rBuffer: {buffer}", end='', flush=True)
            continue

        if char == ';':
            substring = buffer[pos:]
            matched_keys = [key for key in key2ph if key.startswith(substring)]
            if matched_keys:
                print("\n")
                options = []
                for key in matched_keys:
                    for number, phrase in key2ph[key]:
                        options.append((key, number, phrase))
                for idx, (key, number, option) in enumerate(options, start=1):
                    print(f"{idx}: {key}{number} {''.join(option)}")
            buffer += char
            print(f"\rBuffer: {buffer}", end='', flush=True)
            continue

        if char == '`':
            substring = buffer[pos:]
            if len(substring) == 0:
                continue;
            matched_keys = [key for key in keys2word if key.startswith(substring)]
            if matched_keys:
                print("\n")
                options = []
                for key in matched_keys:
                    for phrase in keys2word[key]:
                        # print(f"DEBUG: Processing key={key}, phrase={phrase}")  # Debug 訊息
                        options.append((key, phrase))
                print(format_options(options, width=78))

            buffer += char
            print(f"\rBuffer: {buffer}", end='', flush=True)
            continue
            
        if char == '/':
            substring = buffer[pos:]
            matched_keys = [key for key in keys2word if key == substring]
            if matched_keys:
                print("\n")
                options = []
                for key in matched_keys:
                    for phrase in keys2word[key]:
                        # print(f"DEBUG: Processing key={key}, phrase={phrase}")  # Debug 訊息
                        options.append((key, phrase))
                print(format_options(options, width=78))

            buffer += char
            print(f"\rBuffer: {buffer}", end='', flush=True)
            continue


        if char == ' ':
            # Split the buffer into English + number pairs, adding ';' to the regex
            pairs = re.findall(r'([a-zA-Z;/`]+)(\d+)?', buffer)

            for pair in pairs:
                english, num_str = pair
                num = int(num_str) if num_str else 1  # Default to 1 if no number is provided

                if '/' in english:
                    # Handle logic when '/' is present
                    substring = english.replace('/', '')
                    matched_keys = [key for key in keys2word if key == substring]
                    if matched_keys:
                        options = []
                    for key in matched_keys:
                        for phrase in keys2word[key]:
                            options.append((key, phrase))
                    for idx, (key, option) in enumerate(options, start=1):
                        if num == idx:
                            output_buffer += ''.join(option)
                # Check if ';' exists in the current 'english' part
                elif '`' in english:
                    # Handle logic when '/' is present
                    substring = english.replace('`', '')
                    if len(substring) > 0:
                        matched_keys = [key for key in keys2word if key.startswith(substring)]
                        if matched_keys:
                            options = []
                        for key in matched_keys:
                            for phrase in keys2word[key]:
                                options.append((key, phrase))
                        for idx, (key, option) in enumerate(options, start=1):
                            if num == idx:
                                output_buffer += ''.join(option)
                # Check if ';' exists in the current 'english' part
                elif ';' in english:
                    # Handle logic when ';' is present
                    substring = english.replace(';', '')
                    matched_keys = [key for key in key2ph if key.startswith(substring)]
                    if matched_keys:
                        options = []
                    for key in matched_keys:
                        for number, phrase in key2ph[key]:
                            options.append((key, number, phrase))
                    for idx, (key, number, option) in enumerate(options, start=1):
                        if num == idx:
                            output_buffer += ''.join(option)
                else:
                    # Old logic when ';' is not present
                    if english in key2ph:
                        matched_phrase = next(
                            (phrase_list for number, phrase_list in key2ph[english] if number == num),
                            None
                        )
                        if matched_phrase:
                            output_buffer += ''.join(matched_phrase)
                    else:
                        # 當 key2ph 中無法找到英文單字時，啟用 3 字元分割邏輯
                        current_pos = 0
                        buffer2 = english
                        while len(buffer2[current_pos:]) >= 3:
                            left_chars = buffer2[current_pos:current_pos + 3]
                            mem_index = left_chars[:2]  # 前兩個字元作為 mem2char 的索引
                            offset_char = left_chars[2]  # 第三個字元表示偏移量

                            # 偏移量轉換：從 'a' 開始的索引
                            if 'a' <= offset_char <= 'z':
                                offset = ord(offset_char) - ord('a')  # 偏移量
                                if mem_index in mem2char and offset < len(mem2char[mem_index]):
                                    result_char = mem2char[mem_index][offset]  # 查找對應字元
                                    output_buffer += result_char  # 加入輸出緩衝
                                else:
                                    output_buffer += '?'  # 無效索引或偏移時用占位符
                            else:
                                output_buffer += '?'  # 非 'a'-'z' 範圍字元顯示占位符

                            current_pos += 3  # 更新處理位置
                            english2 = buffer2[current_pos:]
                            if english2 in key2ph:
                                matched_phrase = next(
                                    (phrase_list for number, phrase_list in key2ph[english2] if number == num),
                                    None
                                )
                                if matched_phrase:
                                    output_buffer += ''.join(matched_phrase)
                                pos += current_pos
                                break
                        pos += current_pos
                    
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
            print(hint_string_1)
            continue
            
        if char == '\t':
            print(hint_string_1)
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

        current_pos = pos  # 使用另一個變數追蹤當前處理位置

        # 迴圈處理每 3 個字元，直到剩餘不足 3 個字元
        while len(buffer[current_pos:]) >= 3:
            # 提取左側三個字元
            left_chars = buffer[current_pos:current_pos + 3]
            mem_index = left_chars[:2]  # 前兩個字元作為 mem2char 的索引
            offset_char = left_chars[2]  # 第三個字元表示偏移量
            
            # 偏移量轉換：從 'a' 開始的索引
            if 'a' <= offset_char <= 'z':
                offset = ord(offset_char) - ord('a')  # 偏移量
                if mem_index in mem2char and offset < len(mem2char[mem_index]):
                    result_char = mem2char[mem_index][offset]  # 查找對應字元
                    print(result_char, end='')  # 直接輸出結果字元
                else:
                    print("?", end='')  # 無效索引或偏移時顯示占位符
            else:
                print("?", end='')  # 非 'a'-'z' 範圍字元顯示占位符
            
            current_pos += 3  # 更新處理位置

        # 處理剩餘不足 3 個字元的情況（執行舊邏輯）
        if len(buffer[current_pos:]) == 2:
            print("\n## ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ")
            if buffer[current_pos:] in mem2char:
                result_chars = ''.join(mem2char[buffer[current_pos:]])
                print(f"{buffer[current_pos:]} {result_chars}")

        print(f"\nBuffer: {buffer}", end='', flush=True)

        if buffer[current_pos:] in key2ph:
            options = key2ph[buffer[current_pos:]]
            print("\nOptions:")
            for idx, (number, option) in enumerate(options, start=1):
                print(f"{number}: {''.join(option)}")
            print(f"\rBuffer: {buffer}", end='', flush=True)


if __name__ == "__main__":
    lime_file = 'cuf_keyboard_m01.lime'
    if not os.path.exists(lime_file):
        print(f"Error: {lime_file} not found.")
        exit(1)

    word2pinyin, keys2word = parse_lime_file(lime_file)
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

    input_loop(key2ph, mem2char, keys2word)
