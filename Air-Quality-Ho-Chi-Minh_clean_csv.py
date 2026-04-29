import csv

input_file = r'c:\Users\Acer\source\repos\Nam3_Ki2\tqhdl\final_pj\dataset\Air Quality Ho Chi Minh City.csv'

try:
    with open(input_file, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        header = next(reader)
        
        cleaned_rows = [header]
        total_rows = 1
        for row in reader:
            total_rows += 1
            if len(row) == len(header) and all(cell.strip() != '' for cell in row):
                cleaned_rows.append(row)
                
    with open(input_file, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(cleaned_rows)
        
    print(f'Done! Original: {total_rows}, Cleaned: {len(cleaned_rows)}, Removed: {total_rows - len(cleaned_rows)}')
except Exception as e:
    print(f'Error: {e}')
