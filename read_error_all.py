
with open('indexing_log_final.txt', 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        if "ERROR" in line:
            print(line.strip())
