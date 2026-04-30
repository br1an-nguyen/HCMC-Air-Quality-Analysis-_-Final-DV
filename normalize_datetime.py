import pandas as pd
import os

# Đường dẫn tệp
file_path = r'c:\Users\Acer\source\repos\Nam3_Ki2\tqhdl\final_pj\dataset\Air Quality Ho Chi Minh City.csv'
output_path = r'c:\Users\Acer\source\repos\Nam3_Ki2\tqhdl\final_pj\dataset\Air Quality Ho Chi Minh City Normalized.csv'

def normalize_datetime():
    try:
        # Read data
        print(f"Reading file: {file_path}")
        df = pd.read_csv(file_path)
        
        # Split 'date' column into 'Date' and 'Time'
        if 'date' in df.columns:
            datetime_split = df['date'].str.split(' ', expand=True)
            
            # Assign to new columns
            df.insert(0, 'Date', datetime_split[0])
            df.insert(1, 'Time', datetime_split[1])
            
            # Drop old 'date' column
            df.drop(columns=['date'], inplace=True)
            
            print("Successfully split 'date' into 'Date' and 'Time'.")
        else:
            print("Error: 'date' column not found in CSV file.")
            return

        # Save to new file
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"Normalized file saved at: {output_path}")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    normalize_datetime()
