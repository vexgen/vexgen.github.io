import json
from datetime import datetime, timedelta
import pytz
from selenium import webdriver
from bs4 import BeautifulSoup


##  NVD Dashboard CVE Rate Report Tool
##  Author:  Jamie Aitken
##  Date:    04/2024


## This script was written in a very ad-hoc fashion, so function took precedence over form (and notably functions...) 
## Needs more error checking etc.

## Note: Running this script will spawn a browser window that will close after scraping.

print("NVD CVE Rate Analysis Tool")

# NVD Dashboard URL
url = "https://nvd.nist.gov/general/nvd-dashboard"

# Define the filename that the data will be written to
html_filename = '/home/jamie/development/python/nvdScrape/html/vexgen.github.io/index.html'
json_filename = '/home/jamie/development/python/nvdScrape/html/vexgen.github.io/data.json'

# IMPORTANT!!! - change this to your own browser value (e.g. Chrome). This creates a new instance of the Firefox driver. 
driver = webdriver.Firefox()

# Get today's date
now = datetime.now()

# Get the first day of this year
start_of_year = datetime(year=now.year, month=1, day=1)

# Calculate the number of days that have passed since the start of the year
days_passed_year = (now - start_of_year).days

# Calculate the number of days that have passed since the start of the month
days_passed_month = now.day

# Calculate the number of days that have passed since the start of the week
days_passed_week = now.weekday() + 1  # Monday is 0, Sunday is 6

est = pytz.timezone('US/Eastern')


print("\nSpawning browser...")
# Go to the URL (NVD Dashboard) - This launches a browser window. I found that just using BeautifulSoup wouldn't pull in the data from the HTML (i.e. Number of CVEs Analyzed), 
# just the placeholder values.
# There is probably a better way of doing this.
driver.get(url)

# Get the HTML of the page
html = driver.page_source

# Parse the HTML with BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')

# Find the first table in the returned HTML (CVEs Received and Processed), this table contains Time Period data.
table = soup.find('table', {'id': 'tableCvesReceivedAndProcessed'})

# Find the second table (CVE Status Count), contains Awaiting Analysis etc.
table2 = soup.find('table', {'id': 'tableCveStatusCount'})

# Get the headers of the first table from the thead section
headers = [th.text for th in table.find('thead').find_all('th')]

# Get the rows of the first table from the tbody section
rows = table.find('tbody').find_all('tr')

# Get the rows of the second table from the tbody section
rows2 = table2.find('tbody').find_all('tr')

table_data = []
table_data2 = []

print("\nParsing Data...")

# For each row in data from CVEs Received and Processed table, get the data and store it in a dictionary
for row in rows:
    data = [td.text for td in row.find_all('td')]
    # The first cell in the row is a th, not a td, so get its text separately
    time_period = row.find('th').text
    # Insert the time period (i.e "TODAY") at the start of the data list
    data.insert(0, time_period)
    row_dict = {headers[i]: data[i] for i in range(min(len(headers), len(data)))}
    
    # Calculate the percentage of "New CVEs Analyzed by NVD" out of "New CVEs Received by NVD"
    new_cves_received = int(row_dict['New CVEs Received by NVD'])
    new_cves_analyzed = int(row_dict['New CVEs Analyzed by NVD'])
    if new_cves_received != 0:  # Avoid division by zero
        percentage_analyzed = (new_cves_analyzed / new_cves_received) * 100
    else:
        percentage_analyzed = 0  # If no new CVEs were received, the percentage analyzed is 0
    row_dict['Percent of New CVEs Analyzed'] = f'{percentage_analyzed:.2f}%'

    # Calculate the average for the "This Year", "This Month", "This Week", and "Last Month" rows
    if time_period == 'This Year':
        average = new_cves_analyzed / days_passed_year
    elif time_period == 'This Month':
        average = new_cves_analyzed / days_passed_month
    elif time_period == 'This Week':
        average = new_cves_analyzed / days_passed_week
    elif time_period == 'Last Month':
        average = new_cves_analyzed / 30  # Approximate number of days in a month
    else:
        average = None  # No average for other rows

    if average is not None:
        row_dict['Daily Average New CVEs Analyzed'] = f'{average:.2f}'
    else:
        row_dict['Daily Average New CVEs Analyzed'] = ''  # Empty string for rows without an average
    
    table_data.append(row_dict)

    # Add the calculated percentage to the HTML table
    new_td_percentage = soup.new_tag('td')
    new_td_percentage.string = f'{percentage_analyzed:.2f}%'
    row.append(new_td_percentage)

    # Add the calculated average to the HTML table
    new_td_average = soup.new_tag('td')
    if average is not None:
        new_td_average.string = f'{average:.2f}'
    else:
        new_td_average.string = ''
    row.append(new_td_average)


this_year_average = None
for row in table_data:
    if row['Time Period'] == 'This Year':
        this_year_average = float(row['Daily Average New CVEs Analyzed'])
        break


# For each row, get the data and store it in a dictionary (for "CVE STATUS COUNT" table)
for row in rows2:
    data = [td.text for td in row.find_all('td')]
    # Treat the first td as a header and the second td as a data point
    if len(data) == 2:
        row_dict = {data[0]: data[1]}
        table_data2.append(row_dict)

# Add the new headers to the HTML table
new_th_percentage = soup.new_tag('th')
new_th_percentage.string = 'Percent of New CVEs Analyzed'
table.find('thead').find('tr').append(new_th_percentage)

new_th_average = soup.new_tag('th')
new_th_average.string = 'Daily Average New CVEs Analyzed'
table.find('thead').find('tr').append(new_th_average)

# Get the modified HTML of the page
modified_html = str(soup)

# Don't forget to close the driver
driver.quit()

# Extract the value for "Awaiting Analysis"
awaiting_analysis = None
for row in table_data2:
    if 'Awaiting Analysis' in row:
        awaiting_analysis = int(row['Awaiting Analysis'])
        break

# Initialize the variables
average_new_daily_cves = 0
required_daily_effort = 0

if awaiting_analysis is not None:
    # Calculate the number of days left in the year
    today = datetime.now()
    next_year = datetime(today.year + 1, 1, 1)
    days_left = (next_year - today).days

    # Calculate the result
    result = awaiting_analysis / days_left
    result = round(result, 2)

    # Extract the value for "New CVEs Received by NVD" for "This Year"
    new_cves_this_year = None
    for row in table_data:
        if row['Time Period'] == 'This Year':
            new_cves_this_year = int(row['New CVEs Received by NVD'])
            break

    if new_cves_this_year is not None:
        # Calculate the average new daily CVEs
        average_new_daily_cves = new_cves_this_year / days_passed_year
        average_new_daily_cves = round(average_new_daily_cves, 2)

        # Calculate the required daily effort
        required_daily_effort = average_new_daily_cves + result
        required_daily_effort = round(required_daily_effort, 2)
    else:
        print('Could not find "This Year" in the data')

else:
    print('Could not find "Awaiting Analysis" in the data')

# Calculate the End of Year Forecast (i.e. Estimated CVEs Awaiting Analysis at EOY = 24376.46)
end_of_year_forecast = ((average_new_daily_cves * days_left) + awaiting_analysis)- (this_year_average * days_left)
end_of_year_forecast = round(end_of_year_forecast, 2)

# Short of goal is used in summary statement below to indicate how far off NVD are from hitting the goal to clear New CVEs and Backlog CVEs by EOY
short_of_goal = required_daily_effort - this_year_average
short_of_goal = round(short_of_goal, 2)

## This is the summary statement that is printed at the top of the HTML page under the main title.
summary = '''
    <p>The following estimates are calculated using data from the <a href='https://nvd.nist.gov/general/nvd-dashboard'>NVD Dashboard. </a> At the time of this reports generation, NVD's 2024 daily average for analyzing new CVEs is {}. There is a current backlog of {} CVEs awaiting analysis. With an average influx of {} new CVEs per day, a daily average of {} analyses is required to clear this backlog and process new CVEs. Currently, NVD is falling short of this goal by {} CVEs a day. Given this data, if the current daily rate of CVE analysis persists, the projected number of CVEs awaiting analysis by the end of 2024 will be {}.</p>
'''.format(this_year_average, awaiting_analysis, average_new_daily_cves, required_daily_effort, short_of_goal, end_of_year_forecast)

summary_json = '''<p>The following estimates are calculated using data from the <a href='https://nvd.nist.gov/general/nvd-dashboard'>NVD Dashboard. </a> At the time of this reports generation, NVD's 2024 daily average for analyzing new CVEs is {}. There is a current backlog of {} CVEs awaiting analysis. With an average influx of {} new CVEs per day, a daily average of {} analyses is required to clear this backlog and process new CVEs. Currently, NVD is falling short of this goal by {} CVEs a day. Given this data, if the current daily rate of CVE analysis persists, the projected number of CVEs awaiting analysis by the end of 2024 will be {}.</p>'''.format(this_year_average, awaiting_analysis, average_new_daily_cves, required_daily_effort, short_of_goal, end_of_year_forecast)

print("\nGenerating HTML...")

# Open the filename defined at the top of the script and begin writing HTML

try:

    with open(html_filename, 'w') as f:

        # Write the start of the HTML file. 
        f.write('''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <!-- Include Bootstrap CSS -->
            <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.0/css/bootstrap.min.css">
                <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootswatch/4.5.0/superhero/bootstrap.min.css">
            <title>NVD CVE Analysis Rate Report</title>
            <!-- Add custom CSS -->
            <style>
                body {
                    
                    
                }
                .container {
                    margin-top: 20px;
                }
                table {
                    
                }
                .rounded thead {
                    border-top-left-radius: 10px; 
                    border-top-right-radius: 10px; 
                }
                .rounded tbody {
                    border-bottom-left-radius: 10px; 
                    border-bottom-right-radius: 10px; 
                }
                th {+
                    vertical-align: top;
                }
            </style>
        </head>
        <body>
        <div class="container">
            <h1 class="text-center mb-4">NVD CVE Analysis Rate Report</h1>
                
            
        ''')

        # Main Body Data


        # Write the summary statement
        f.write(summary)

        # Add 'Percentage Analyzed' to headers
        headers.extend(['Percent of New CVEs Analyzed', 'Daily Average New CVEs Analyzed'])

        # Write the headers
        f.write('<table class="table table-striped table-hover"><thead><tr>' + ''.join([f'<th scope="col">{header}</th>' for header in headers]) + '</tr></thead>\n')

        # Write the data
        f.write('<tbody>\n')
        for row in table_data:
            f.write('<tr>' + ''.join([f'<td>{row.get(header, "")}</td>' for header in headers]) + '</tr>\n')
        f.write('</tbody>\n')

        # Write the end of the first table
        f.write('</table>\n')

        # Write the second table (2024 Backlog + Daily New CVE Effort Requirements) data
        # This may be refered to as table 3 in place due to layout changes. Confusing, should fix.
        f.write('<h2 class="text-center mb-4 mt-5">2024 Backlog + Daily New CVE Effort Requirements</h2>\n')

        f.write('<p>The following table provides an estimate of the daily average required to analyze the backlog of CVEs awaiting analysis by the end of 2024. The estimate is based on the assumption that new CVEs are received and analyzed 7 days a week.</p>\n')

        # Write the start of the second table
        f.write('<table class="table table-striped rounded table-hover">\n')

        # Write the headers for the second table
        f.write('<thead><tr><th>CVEs Awaiting Analysis</th><th>Days Left in 2024</th><th>Daily Average Required to Analyze Backlog</th><th>Average New Daily CVEs (2024)</th><th>2024 Required Total Daily Effort (Avg. Daily New CVEs + Backlog CVEs)</th></tr></thead>\n')

        # Write the data for the second table
        f.write('<tbody>\n')
        f.write(f'<tr><td>{awaiting_analysis}</td><td>{days_left}</td><td>{result}</td><td>{average_new_daily_cves}</td><td>{required_daily_effort}</td></tr>\n')
        f.write('</tbody>\n')

        # Write the end of the second table
        f.write('</table>\n')



        # Write the title for the Forecast table
        f.write('<h2 class="text-center mb-4 mt-5">End of Year Estimate</h2>\n')

        f.write('<p>The following table provides an estimate of the number of CVEs awaiting analysis at the end of 2024 based on the average number of new daily CVEs and the number of days left in the year. The estimate is based on the assumption that new CVEs are received and analyzed 7 days a week.</p>\n')

        # Write the start of the Forecast table
        f.write('<div class="rounded overflow-hidden">\n')
        f.write('<table class="table table-striped table-hover">\n')

        # Write the headers for the Forecast table
        f.write('<thead><tr><th>Average New Daily CVEs</th><th>CVEs Awaiting Analysis</th><th>Days Left in 2024</th><th>2024 Daily New CVE Analysis Average</th><th>Estimated CVEs Awaiting Analysis at EOY</th></tr></thead>\n')

        # Write the data for the Forecast table
        f.write('<tbody>\n')
        f.write(f'<tr><td>{average_new_daily_cves}</td><td>{awaiting_analysis}</td><td>{days_left}</td><td>{this_year_average}</td><td>{end_of_year_forecast}</td></tr>\n')
        f.write('</tbody>\n')

        # Write the end of the Forecast table
        f.write('</table>\n')
        f.write('</div>\n')


        # Write the timestamp at the bottom of the page
        f.write(f'<p class="text-right mt-4">Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} PST</p>\n')

        # Write the end of the container and the HTML file
        f.write('</div></body></html>')
    
except Exception as e:
    print(f"\nFailure: {e}")

else:
    print(f"\n{html_filename} written successfully...")
    

# Adding JSON output

json_data = {

    # Timestamp of when the JSON file was generated
    'timestamp': datetime.now(est).strftime('%Y-%m-%d %H:%M:%S'),

    # Summary statement that is printed at the top of the HTML page under the main title.
    'summary': summary_json,

    # daily_average_new_cves_analyzed is the daily average for analyzing new CVEs for the current year
    'daily_average_new_cves_analyzed': this_year_average,
    # cves_awaiting_analysis is the number of CVEs currently awaiting analysis by NVD (the backlog)
    'cves_awaiting_analysis': awaiting_analysis,
    # required_daily_effort is the daily average required to analyze the backlog of CVEs awaiting analysis and new CVEs by the end of 2024
    'required_daily_effort': required_daily_effort,
    # short_of_goal is used in summary statement below to indicate how far off NVD are from hitting the goal to clear New CVEs and Backlog CVEs by EOY
    'short_of_goal': short_of_goal,

    # Table 1: CVEs Received and Processed
    'table_data': table_data,

    # days_left_in_2024 is the number of days left in the year
    'days_left_in_2024': days_left,

    # average_new_daily_cves is the average number of new daily CVEs for the current year
    'average_new_daily_cves': average_new_daily_cves,
    
    # end_of_year_forecast is the estimated number of CVEs awaiting analysis at the end of 2024
    'estimated_cves_awaiting_analysis_at_eoy': end_of_year_forecast

}

json_output = json.dumps(json_data, indent=4)

with open(json_filename, 'w') as f:
    f.write(json_output)

print("\nJSON output written successfully...")
print("\nExiting...")
