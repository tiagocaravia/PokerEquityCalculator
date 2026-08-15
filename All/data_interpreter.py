import csv 

with open('Standard5.csv', 'r') as file:
    reader = csv.reader(file)
    data = list(reader)

