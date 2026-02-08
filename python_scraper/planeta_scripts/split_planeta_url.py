import os

def split_file(input_file, num_chunks):
    folder = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(folder, input_file)
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    chunk_size = (len(lines) + num_chunks - 1) // num_chunks
    for i in range(num_chunks):
        chunk_lines = lines[i*chunk_size:(i+1)*chunk_size]
        out_path = os.path.join(folder, f'planeta_urls_{i+1}.txt')
        with open(out_path, 'w', encoding='utf-8') as out:
            out.write('\n'.join(chunk_lines))
    print(f"Split into {num_chunks} files.")

if __name__ == "__main__":
    split_file('planeta_proizvodi_bez_sifre.txt', 9)