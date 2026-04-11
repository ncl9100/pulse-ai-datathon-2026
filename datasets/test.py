import pandas as pd

df = pd.read_csv('./labor_logs_all.csv')

# print value counts for the column 'role'

print(df['role'].value_counts())