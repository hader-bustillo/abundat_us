from __future__ import print_function
import boto3
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import interactive
import matplotlib.dates
import dateutil.parser
import datetime
import pdb
import glob
import dynamo
from boto3.dynamodb.conditions import Key, Attr

#create table for insertion
def createTimeSeriesTable():

    dynamodb = boto3.client('dynamodb')

    table = dynamodb.create_table(
        TableName='RS_ARTICLE_TIMESERIES',
        KeySchema=[
            {
                'AttributeName': 'page',
                'KeyType': 'HASH'  #Partition key
            },

            {
                'AttributeName': 'date',
                'KeyType': 'RANGE'  # Sort key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'page',
                'AttributeType': 'S'
            },

            {
                'AttributeName': 'date',
                'AttributeType': 'S'
            }

        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 20,
            'WriteCapacityUnits': 10
        }
    )

    print('Created Table.')

    return

#delete table
def resetTable():

    dynamodb = boto3.client('dynamodb')
    dynamodb.delete_table(TableName='RS_ARTICLE_TIMESERIES')

    return 'Table Reset.'

def plotData(week, data, compare):


    f, ax = plt.subplots(1)
    f.suptitle(compare)
    ax.plot(week, data, linestyle='-', marker='o', color='b')
    ax.set_ylim(ymin=0)
    #plt.show()
    plt.savefig('./timeseries/' + compare + '.png')

    return

#insert data from specified CSV sheet (times must be specified since information is not found in the sheet)
def testDynamoPut():

    week = [datetime.datetime(2018, 11, 25), datetime.datetime(2018, 11, 26), datetime.datetime(2018, 11, 27),
            datetime.datetime(2018, 11, 28), datetime.datetime(2018, 11, 29), datetime.datetime(2018, 11, 30),
            datetime.datetime(2018, 12, 1)]

    weeklyFiles = glob.glob('./timeseries/Weekly/*')
    sortedFiles = []

    for csv in weeklyFiles:
        day = csv.split('-')[-1]
        if not '0' in day:
            sortedFiles.append(csv)
        else:
            first = csv

    sortedFiles = sorted(sortedFiles, key=lambda x: x.split('-')[-1][0], reverse=True)
    sortedFiles.append(first)

    for n, day in enumerate(sortedFiles):

        print('adding: ' + str(day))

        csv_file = pd.read_csv(day)

        for i, row in csv_file.iterrows():

            dataObject = eval(row.to_json().replace('null', "'N/A'"))
            dataObject['page'] = dataObject['Page']
            dataObject.pop('Page')
            dataObject['CTR'] = dataObject['CTR'].replace('%', '')
            dataObject['Position'] = str(dataObject['Position'])
            dataObject['date'] = week[n].isoformat()

            dynamo.dynamo_put_item('RS_ARTICLE_TIMESERIES', dataObject)

    return 'Done!'

#get all files in between two dates
def getItemsFromDates(table, start, stop):

    fe = Key('date').between(start, stop)
    response = table.scan(FilterExpression=fe)

    return response['Items']

#plot data between two dates
def testDynamoGet():
    session = boto3.session.Session(profile_name='default', region_name='us-east-2')
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table('RS_ARTICLE_TIMESERIES')

    start = '2018-11-25'
    stop = '2018-12-03'

    dataDump = getItemsFromDates(table, start, stop)

    dateRange = []
    timeObj = {}

    for item in dataDump:

        dateObject = dateutil.parser.parse(item['date'])
        found = False

        for i in dateRange:
            if i['date'] == dateObject:
                i['CTR'] += float(item['CTR'])
                i['Impressions'] += item['Impressions']
                i['Position'] += float(item['Position'])
                i['Clicks'] += item['Clicks']
                i['length'] += 1
                found = True
                break

        if not found:
            timeObj['date'] = dateObject
            timeObj['CTR'] = float(item['CTR'])
            timeObj['Impressions'] = item['Impressions']
            timeObj['Position'] = float(item['Position'])
            timeObj['Clicks'] = item['Clicks']
            timeObj['length'] = 0
            dateRange.append(timeObj)
            timeObj = {}

    dates = []
    ctrList = []
    clicksList = []
    impressionsList = []
    avgRankingList = []

    dateRange = sorted(dateRange, key=lambda x: x['date'])

    for item in dateRange:
        item['avgCTR'] = item['CTR'] / item['length']
        item['avgPosition'] = item['Position'] / item['length']
        dates.append(item['date'])
        ctrList.append(item['avgCTR'])
        clicksList.append(item['Clicks'])
        impressionsList.append(item['Impressions'])
        avgRankingList.append(item['avgPosition'])

    plotData(dates, clicksList, 'Clicks')
    plotData(dates, ctrList, 'CTR')
    plotData(dates, impressionsList, 'Impressions')
    plotData(dates, avgRankingList, 'Average Ranking')

    return


########### END OF DYNAMO ################

#vizualize excel monthly data
def createDataObjectsByMonth():

    #gets file path of monthly articles
    weeklyFiles = glob.glob('./timeseries/Monthly/*')

    timeList = []
    timeObject = {}

    for day in weeklyFiles:

        excel_file = pd.read_excel(day, 'Summary')

        for i, row in excel_file.iterrows():

            dataObject = eval(row.to_json().replace('null', "'N/A'"))
            if '-' in dataObject['All Web Site Data']:

                dates = dataObject['All Web Site Data'].split('-')
                fromDateMonth = dates[0][:-2][4:]
                fromDateDay = dates[0][-2:]
                toDateMonth = dates[1][:-2][4:]
                toDateDay = dates[1][-2:]

                timeObject['dateFrom'] = datetime.datetime(2018, int(fromDateMonth), int(fromDateDay))
                timeObject['date'] = datetime.datetime(2018, int(toDateMonth), int(toDateDay))
                timeObject['file'] = day

                timeList.append(timeObject)
                timeObject = {}

    sortedFiles = sorted(timeList, key=lambda x: x['date'])
    timePeriod = [sortedFiles[0]['dateFrom']] + [d['date'] for d in sortedFiles]
    sortedFiles = [f['file'] for f in sortedFiles]

    exitRateList = [0]
    bounceRateList = [0]
    timeOnPageList = [0]
    uVistorsList = [0]
    articleViewCountList = [0]

    exitRate = 0.0
    bounceRate = 0.0
    timeOnPage = 0.0
    uVisitors = 0
    articleViewCount = 0

    for day in sortedFiles:

        excel_file = pd.read_excel(day, 'Dataset1')

        for i, row in excel_file.iterrows():

            dataObject = eval(row.to_json().replace('null', "'N/A'"))

            if dataObject['Page'] != 'N/A':

                exitRate += dataObject['% Exit']
                bounceRate += dataObject['Bounce Rate']
                uVisitors += dataObject['Unique Pageviews']
                timeOnPage += dataObject['Avg. Time on Page']
                if dataObject['Pageviews'] > 0:
                    articleViewCount += dataObject['Pageviews']

        length = i + 1

        avgExitRate = (exitRate / length)
        avgBounceRate = (bounceRate / length)
        avgTimeOnPage = (timeOnPage / length)
        avgUVistors = int(uVisitors / length)
        avgViewCount = int(articleViewCount / length)

        exitRateList.append(avgExitRate)
        bounceRateList.append(avgBounceRate)
        timeOnPageList.append(avgTimeOnPage)
        uVistorsList.append(avgUVistors)
        articleViewCountList.append(avgViewCount)

        exitRate = 0.0
        bounceRate = 0.0
        timeOnPage = 0.0
        uVisitors = 0
        articleViewCount = 0

    plotData(timePeriod, exitRateList, 'Avg. Exit Rate vs Time')
    plotData(timePeriod, bounceRateList, 'Avg. Bounce Rate vs Time')
    plotData(timePeriod, timeOnPageList, 'Avg. Time On Page vs Time')
    plotData(timePeriod, uVistorsList, 'Avg. Unique Visitors vs Time')
    plotData(timePeriod, articleViewCountList, 'Avg. Page Views vs Time')

    return

#vizualizations of weekly data from CSVs
def createDataObjectsByWeek():

    week = [datetime.datetime(2018, 11, 25), datetime.datetime(2018, 11, 26), datetime.datetime(2018, 11, 27),
            datetime.datetime(2018, 11, 28), datetime.datetime(2018, 11, 29), datetime.datetime(2018, 11, 30),
            datetime.datetime(2018, 12, 1)]

    #gets file path of weekly articles
    weeklyFiles = glob.glob('./timeseries/Weekly/*')
    sortedFiles = []

    ctrList = []
    clicksList = []
    articleViewCountList = []
    impressionsList = []
    avgRankingList = []

    clickThrough = 0
    clicks = 0
    articleViewCount = 0
    impressions = 0
    avgRanking = 0.0

    for csv in weeklyFiles:
        day = csv.split('-')[-1]
        if not '0' in day:
            sortedFiles.append(csv)
        else:
            first = csv

    sortedFiles = sorted(sortedFiles, key=lambda x: x.split('-')[-1][0], reverse=True)
    sortedFiles.append(first)

    for day in sortedFiles:

        csv_file = pd.read_csv(day)

        for i, row in csv_file.iterrows():

            dataObject = eval(row.to_json().replace('null', "'N/A'"))

            clickThrough += float(dataObject['CTR'].replace('%', ''))
            clicks += dataObject['Clicks']
            impressions += dataObject['Impressions']
            avgRanking += dataObject['Position']
            if dataObject['Impressions'] > 0:
                articleViewCount += 1

        length = i + 1
        avgRanking = int(avgRanking / length)
        avgCTR = clickThrough / length

        ctrList.append(avgCTR)
        clicksList.append(clicks)
        impressionsList.append(impressions)
        articleViewCountList.append(articleViewCount)
        avgRankingList.append(avgRanking)

        clickThrough = 0
        clicks = 0
        articleViewCount = 0
        impressions = 0
        avgRanking = 0.0

    plotData(week, clicksList, 'Clicks')
    plotData(week, ctrList, 'CTR')
    plotData(week, articleViewCountList, 'View Count')
    plotData(week, impressionsList, 'Impressions')
    plotData(week, avgRankingList, 'Average Ranking')

    return


if __name__ == "__main__":
    #resetTable()
    #createTimeSeriesTable()
    #testDynamoPut()
    testDynamoGet()