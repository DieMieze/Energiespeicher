# Import necessary libraries\n",
    "import pandas as pd\n",
    "import os\n",
    "\n",
    "# Define file paths\n",
    "data_dir = 'data/'  # Directory containing CSV files\n",
    "output_dir = 'output/'  # Directory to save organized text files\n",
    "\n",
    "# Create output directory if it doesn't exist\n",
    "os.makedirs(output_dir, exist_ok=True)\n",
    "\n",
    "# Define file names\n",
    "verbrauch_file = os.path.join(data_dir, 'Realisierter_Stromverbrauch_202401010000_202501010000_Viertelstunde.csv')\n",
    "produktion_file = os.path.join(data_dir, 'Realisierte_Erzeugung_202401010000_202501010000_Viertelstunde.csv')\n",
    "preise_file = os.path.join(data_dir, 'Gro_handelspreise_202401010000_202501010000_Stunde.csv')\n",
    "\n",
    "# Read CSV files\n",
    "verbrauch = pd.read_csv(verbrauch_file, sep=';', decimal=',', thousands='.', parse_dates=['Datum von', 'Datum bis'], dayfirst=True)\n",
    "produktion = pd.read_csv(produktion_file, sep=';', decimal=',', thousands='.', parse_dates=['Datum von', 'Datum bis'], dayfirst=True)\n",
    "preise = pd.read_csv(preise_file, sep=';', decimal=',', thousands='.', parse_dates=['Datum von', 'Datum bis'], dayfirst=True)\n",
    "\n",
    "# Normalize data year by year\n",
    "def normalize_data(df, year_col='Datum von'):\n",
    "    df['Year'] = df[year_col].dt.year\n",
    "    return df.groupby('Year').sum().reset_index()\n",
    "\n",
    "verbrauch_normalized = normalize_data(verbrauch)\n",
    "produktion_normalized = normalize_data(produktion)\n",
    "\n",
    "# Save normalized data to text files\n",
    "verbrauch_normalized.to_csv(os.path.join(output_dir, 'verbrauch_normalized.txt'), sep=';', index=False)\n",
    "produktion_normalized.to_csv(os.path.join(output_dir, 'produktion_normalized.txt'), sep=';', index=False)\n",
    "\n",
    "# Calculate average annual surplus and loss\n",
    "def calculate_surplus_loss(verbrauch_df, produktion_df):\n",
    "    merged = pd.merge(verbrauch_df, produktion_df, on='Year', suffixes=('_verbrauch', '_produktion'))\n",
    "    merged['Surplus'] = merged['produktion'] - merged['verbrauch']\n",
    "    average_surplus = merged['Surplus'].mean() / merged['verbrauch'].mean() * 100  # as percentage\n",
    "    average_loss = merged['Surplus'][merged['Surplus'] < 0].mean()  # average loss\n",
    "    return average_surplus, average_loss\n",
    "\n",
    "average_surplus, average_loss = calculate_surplus_loss(verbrauch_normalized, produktion_normalized)\n",
    "\n",
    "# Display results\n",
    "print(f'Average Annual Surplus: {average_surplus:.2f}%')\n",
    "print(f'Average Annual Loss: {average_loss:.2f} MWh')"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.8.5"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
```

### Explanation of the Notebook:

1. **Imports**: The notebook imports necessary libraries such as `pandas` for data manipulation and `os` for file handling.

2. **File Paths**: It defines the paths for the input CSV files and the output directory where the organized text files will be saved.

3. **Reading CSV Files**: The notebook reads the CSV files into pandas DataFrames.

4. **Normalization Function**: A function `normalize_data` is defined to normalize the data year by year.

5. **Saving Normalized Data**: The normalized data is saved into text files in the specified output directory.

6. **Surplus and Loss Calculation**: A function `calculate_surplus_loss` calculates the average annual surplus (as a percentage of annual consumption) and the average annual loss.

7. **Results Display**: Finally, the results are printed to the console.

### Customization:
- Adjust the file paths and names as necessary.
- Modify the normalization logic if your data structure requires it.
- Ensure that the columns used in calculations match those in your CSV files.

You can copy this code into a new Jupyter Notebook cell and run it to perform the analysis.