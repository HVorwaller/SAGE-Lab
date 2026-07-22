import math
import pandas as pd
from pathlib import Path

'''
This program reads the CSV output files from the DLS machine in Dave Estrada's lab, sent from Hailey Burgoyne and outputs
Full Width Half Maximum calculations

    This searching algorithm works by iterating through each analysis' intensity column and finds the first row that is closest to 50 on the
    rising edge, the peak (when intensity is 100), and the second row that is closest to 50 on the falling edge. It calculates the FWHM value
    & log of that value and stores the diameter at the rising edge 50 mark, the diameter at the peak, the diameter at the falling edge 50 mark,
    the FWHM value, and the log of the FWHM value in a dictionary for each analysis.

NOTE: This program does not play as well with CSV files with high polydispersity/multiple populations.
'''

# Get target folder from user
print(f"\nPut all of your CSV files in a single folder (within the current directory). This program will read all CSV files in that folder and output the extracted data.\n")
target_folder = input("Type the name of the folder containing CSVs: ")
folder_path = Path('.') / target_folder

num_decimals = input(f"Type the number of decimal places to round FWHM and Log(FWHM) (defaults to 2): ")
print() # extra line for spacing
try:
    num_decimals = int(num_decimals) if num_decimals != None else 2
except ValueError:
    print("Invalid input. Using default value of 2.")
    num_decimals = 2

# Safety check
if folder_path.exists() and folder_path.is_dir():
    csv_folder = list(folder_path.glob('*.csv'))

    # Master dictionary to hold each file's dictionary of data
    folder_extracted_data = {}
        
    # Iterate through each file in folder
    for csv_file in csv_folder: # csv_file is a Path object (kind of like a pointer to a specific file)
        print(f"Reading: {csv_file.name}")

        # Store the data for this specific file in a placeholder dictionary
        file_extracted_data = {}

        # Read CSV (skip first row)
        df = pd.read_csv(csv_file, skiprows=1) # this is a table that contains the data from the CSV file, with columns and rows
              
        # Step 1: Find the target columns dynamically.

        data_set_number = 1 # indexes for file_extracted_data dictionary
        
        # Loop through the columns by steps of 3 (1, 4, 7, 10...)
        for intensity_col_index in range(1, len(df.columns), 3): # Java equivalent: for (int intensity_col_index = 1; intensity_col_index < df.columns.length; intensity_col_index += 3)
            value_col_index = intensity_col_index - 1  # The column to the left of intensity column is the diameter column
            
            '''
            Iterate through each row in the intensity column to locate the first row that has the closest intensity to 50
            on the rising edge, the peak, and second row that has the closest intensity to 50 on the falling edge.
            '''
            intensity_cell_value = None # store value of current cell in intensity column
            curr_intensity_diff = None # store the absolute difference between the current cell value and 50

            curr_closest_diff = 100 # store the current closest difference between a cell and 50.
                                    # This is initialized to 100 so that the first cell will always
                                    # be closer to 50 than this initial value.
            curr_closest_row_index = None # store the row index of the current closest value

            last_row_index = len(df) - 1 # store the last row index of the intensity column

            diameter_rising = None # store the grain diameter corresponding to the rising edge
            diameter_peak = None # store the grain diameter corresponding to the peak
            diameter_falling = None # store the grain diameter corresponding to the falling edge
            fwhm_value = None # store the calculated fwhm value
            log_fwhm_value = None # store the log of the calculated fwhm value

            for curr_row_index in range(len(df)):
                try:
                    intensity_cell_value = df.iloc[curr_row_index, intensity_col_index]
                    curr_intensity_diff = abs(intensity_cell_value - 50)

                    # Check for rising & falling edge
                    if (curr_intensity_diff < curr_closest_diff):
                        curr_closest_row_index = curr_row_index # Update the current closest row index
                        curr_closest_diff = curr_intensity_diff # Update the current closest difference
                    curr_closest_diff = curr_intensity_diff # Update the previous difference for the next iteration

                    # Check if the current cell value is the peak intensity
                    if (intensity_cell_value == 100):
                        diameter_peak = float(df.iloc[curr_row_index, value_col_index]) # Store peak diameter
                        diameter_rising = float(df.iloc[curr_closest_row_index, value_col_index]) # Lock in rising edge diameter now that peak is reached
                        curr_closest_diff = 100 # reset monitoring to intensity falling edge

                    # Check if the current row is the last row in the intensity column
                    if (curr_row_index == last_row_index):
                        diameter_falling = float(df.iloc[curr_closest_row_index, value_col_index]) # Lock in falling edge diameter now that last row is reached

                except Exception as e:
                    # Safely skip if a column doesn't have numeric data or if we run out of columns
                    break

            # Calculate fwhm and log_fwhm
            if (diameter_rising != None and diameter_falling != None):
                fwhm_value = diameter_falling - diameter_rising # diameter_falling is always larger than diameter_rising
                
                if (fwhm_value > 0):
                    log_fwhm_value = math.log10(fwhm_value)

            # Save all five values in a temporary dictionary
            file_extracted_data[str(data_set_number)] = {
                "diameter_rising": diameter_rising,
                "diameter_peak": diameter_peak,
                "diameter_falling": diameter_falling,
                "fwhm": round(fwhm_value, num_decimals) if fwhm_value != None else None,
                "log_fwhm": round(log_fwhm_value, num_decimals) if log_fwhm_value != None else None
            }

            data_set_number += 1
        
        # Save this file's data into our master dictionary
        folder_extracted_data[csv_file.name] = file_extracted_data

    # --- Print the Final Summary ---
    for filename, data_set in folder_extracted_data.items():
        print(f"\n File: {filename}")
        for label, val in data_set.items():
            print(f"  Analysis {label}: {val}")

    # --- Manage CSV functionality ---
    export_csv = input("\nWould you like to export these results as a CSV file? (y/n): ")

    if (export_csv == "y" or export_csv == "Y" or export_csv == "yes" or export_csv == "Yes"):
        output_rows = [] # list to hold the rows of the output CSV file

        # turn the nested dictionary into a list of rows for the CSV file
        for filename, data_sets in folder_extracted_data.items():
            for label, val in data_sets.items():
                row = {
                    "File": filename,
                    "Analysis": label,
                    "Diameter_Rising": val.get("diameter_rising"),
                    "Diameter_Peak": val.get("diameter_peak"),
                    "Diameter_Falling": val.get("diameter_falling"),
                    "FWHM": val.get("fwhm"),
                    "Log_FWHM": val.get("log_fwhm")
                }
                output_rows.append(row)

        # Create a DataFrame from the list of rows
        summary_df = pd.DataFrame(output_rows)

        # Export the DataFrame to a CSV file
        output_filename = folder_path / f"{target_folder}_FWHM_Results.csv"

        summary_df.to_csv(output_filename, index=False)
        print(f"\nResults exported to: {output_filename.resolve()}")

else:
    print(f"\n Error: The folder '{target_folder}' does not exist.")
