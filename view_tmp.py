# Python script: view_tmp.py
def process_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for word in file:
                # Match lines with [a-z][a-z] followed by a space
                if word[:2].isalpha() and word[2:3] == ' ':
                    print(f"{word.strip().upper()} \n## ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ")
                else:
                    print(word.strip())
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Replace 'tmp_tksm_words.txt' with the actual path to your file
if __name__ == "__main__":
    file_path = 'tmp_tksm_words.txt'
    process_file(file_path)
