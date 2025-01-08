import os
import sys
import termios
import tty
from collections import defaultdict

# 讀取鍵盤輸入
class Getch:
    def __call__(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

getch = Getch()

# 讀取 pinyin.cin 文件
def load_pinyin_cin(filename):
    key2ph = defaultdict(list)
    with open(filename, 'r', encoding='utf-8') as f:
        chardef = False
        for line in f:
            line = line.strip()
            if line == "%chardef begin":
                chardef = True
            elif line == "%chardef end":
                chardef = False
            elif chardef and line:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0]
                    char = parts[1]
                    key2ph[key].append(char)
    return key2ph

# 讀取 word*.txt 文件
def load_word_files(pattern):
    key2ph = defaultdict(list)
    for filename in [f for f in os.listdir('.') if f.startswith(pattern) and f.endswith('.txt')]:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split()
                    if len(parts) >= 2:
                        word = parts[0]
                        pinyin = parts[1]
                        key2ph[pinyin].append(word)
    return key2ph

# 打印候選項目
def display_candidates(candidates):
    for idx, candidate in enumerate(candidates, start=1):
        print(f"{idx}. {candidate}", end='  ')
    print()

# 主程式
if __name__ == "__main__":
    try:
        key2ph = load_pinyin_cin('pinyin.cin')
        word_files = load_word_files('word')
        for key, words in word_files.items():
            key2ph[key].extend(words)

        buffer = []
        max_line_length = 20

        print("拼音輸入法 (按 Ctrl-C 或 Ctrl-D 退出，按 ~ 查看完整候選表)")
        current_input = ""

        while True:
            ch = getch()

            if ch in ('\x03', '\x04'):  # Ctrl-C 或 Ctrl-D
                print("\n退出程式.")
                break

            elif ch == '~':  # 查看完整候選表
                print("完整候選表:")
                for key, words in key2ph.items():
                    print(f"{key}: {' '.join(words)}")

            elif ch == ' ':  # 確認當前選擇
                if current_input in key2ph:
                    candidates = key2ph[current_input]
                    if len(candidates) == 1:
                        buffer.append(candidates[0])
                    else:
                        print("請選擇候選項目 (輸入數字):")
                        display_candidates(candidates)
                        choice = ""
                        while not choice.isdigit() or not (1 <= int(choice) <= len(candidates)):
                            choice = getch()
                        buffer.append(candidates[int(choice) - 1])
                    current_input = ""
                else:
                    print("無匹配項，請繼續輸入。")

                # 處理緩衝區輸出
                current_line = "".join(buffer)
                if len(current_line) >= max_line_length:
                    print(current_line[:max_line_length])
                    buffer = [current_line[max_line_length:]]
                else:
                    print(current_line)

            elif ch.isalpha():  # 輸入拼音
                current_input += ch
                if current_input in key2ph:
                    print(f"匹配: {current_input}")
                    display_candidates(key2ph[current_input])
                else:
                    print(f"當前輸入: {current_input}")

            else:
                print(f"無效輸入: {ch}")

    except Exception as e:
        print(f"發生錯誤: {e}")
