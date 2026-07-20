import pandas as pd
from pathlib import Path

'''
This program reads the CSV output files from the DLS machine in Dave Estrada's lab, sent from Hailey Burgoyne and outputs
Full Width Half Maximum calculations

NOTE: This program does not play well with CSV files with high polydispersity/multiple populations
'''
# Get target folder from user
target_folder = input("Type the name of the folder containing CSVs: ")
folder_path = Path('.') / target_folder

# Store final extracted results for each file in dictionary
extracted_results = {}

if folder_path.exists() and folder_path.is_dir():
    csv_folder = list(folder_path.glob('*.csv'))
    
    # Iterate through each file in folder
    for csv_file in csv_folder:
        print(f"{csv_file.name}: ")
        
        # Read CSV (skip first row)
        df = pd.read_csv(csv_file, skiprows=1)
        
        # Store the pairs for this specific file in a sub-dictionary
        fwhm_pairs = {}
        
        # Step 1: Find the target columns dynamically.
        # Pairs are in the form: check Col 1>read Col 0, Col 4>Col 3, Col 7>Col 6...

        pair_number = 1
        # Loop through the columns by steps of 3 (1, 4, 7, 10...)
        for check_col_index in range(1, len(df.columns), 3):
            value_col_index = check_col_index - 1  # The column right before it
            
            try:
                # 1. Find the row index where the peak (maximum value) occurs
                peak_row_index = df.iloc[:, check_col_index].idxmax()
                
                # 2. Split the check column into rising and falling halves
                rising_half = df.iloc[:peak_row_index, check_col_index]
                falling_half = df.iloc[peak_row_index:, check_col_index]
                
                # 3. Find the row closest to 50 on the rising edge
                index_rising = (rising_half - 50).abs().indexmin()
                # Grab the corresponding x-value from the value column
                x_rising = df.iloc[index_rising, value_col_index]
                
                # 4. Find the row closest to 50 on the falling edge
                index_falling = (falling_half - 50).abs().indexmin()
                # Grab the corresponding x-value from the value column
                x_falling = df.iloc[index_falling, value_col_index]
                
                # 5. Calculate the fwhm (Width = X_falling - X_rising)
                fwhm_value = abs(x_falling - x_rising)
                
                # Save all three values in a structured dictionary for this condition
                fwhm_pairs[str(pair_number)] = {
                    "Rising_Edge_X": x_rising,
                    "Falling_Edge_X": x_falling,
                    "fwhm": fwhm_value
                }

                pair_number += 1
                
            except Exception as e:
                # Safely skip if a column doesn't have numeric data or if we run out of columns
                break
        
        # Save this file's pairs into our master dictionary
        extracted_results[csv_file.name] = fwhm_pairs

    # --- Print the Final Summary ---
    for filename, pairs in extracted_results.items():
        print(f"\n File: {filename}")
        for label, val in pairs.items():
            print(f"  Condition '{label}': {val}")

else:
    print(f"\n Error: The folder '{target_folder}' does not exist.")