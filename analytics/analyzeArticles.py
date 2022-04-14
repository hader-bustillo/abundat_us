import pandas as pd
import argparse
import math
import pdb

"""
Clickthrough (SUM)
Exit rate (AVERAGE)
Bounce Rate (AVERAGE)
NUMBER OF of
    Clicks (SUM)
    Unique Visitors (SUM)
    Articles with views
AVERAGE OF
    Clicks/Article
    Unique Visitors
    Articles with Views per time period (week, month, year)
    Time on page
    Google Search Ranking
Best performing articles (top 2%, 5%, 10%, and 20%)
    Number of clicks
    Number of unique visitors
    Average time on page
    Exit rate
    Bounce rate
    Average Google Search Ranking
Worst Performing Articles (bottom 2%, 5%, 10% and 20%)

csv:
Pages,Clicks,Impressions,CTR,Position
"""

# generating lists of the top performing articles (2,5,10,20) %
def sortKey(obj, field, lowestFirst, pageField):

    topArticles = {}
    worstArticles = {}

    length = len(obj)

    two = int(length * 0.02)
    five = int(length * 0.05)
    ten = int(length * 0.1)
    twenty = int(length * 0.2)

    if lowestFirst:
        sortedObj = sorted(obj, key=lambda k: k[field])
    else:
        sortedObj = sorted(obj, key=lambda k: k[field], reverse=True)

    topArticles['two'] = [a for a in sortedObj[0:two]]
    topArticles['five'] = [a for a in sortedObj[0:five]]
    topArticles['ten'] = [a for a in sortedObj[0:ten]]
    topArticles['twenty'] = [a for a in sortedObj[0:twenty]]

    worstArticles['two'] = [a for a in sortedObj[-two:]]
    worstArticles['five'] = [a for a in sortedObj[-five:]]
    worstArticles['ten'] = [a for a in sortedObj[-ten:]]
    worstArticles['twenty'] = [a for a in sortedObj[-twenty:]]

    return topArticles, worstArticles

# write excel pages for best articles
def writeBestSheets(writer, sheetName, data):


    sheet2Frame = pd.DataFrame(data['two'])
    sheet2Frame.to_excel(writer, 'top2Percent' + sheetName, index=False)
    sheet3Frame = pd.DataFrame(data['five'])
    sheet3Frame.to_excel(writer, 'top5Percent' + sheetName, index=False)
    sheet4Frame = pd.DataFrame(data['ten'])
    sheet4Frame.to_excel(writer, 'top10Percent' + sheetName, index=False)
    sheet5Frame = pd.DataFrame(data['twenty'])
    sheet5Frame.to_excel(writer, 'top20Percent' + sheetName, index=False)

    return

# write excel pages for worst articles
def writeWorstSheets(writer, sheetName, data):

    sheet2Frame = pd.DataFrame(data['two'])
    sheet2Frame.to_excel(writer, 'bottom2Percent' + sheetName, index=False)
    sheet3Frame = pd.DataFrame(data['five'])
    sheet3Frame.to_excel(writer, 'bottom5Percent' + sheetName, index=False)
    sheet4Frame = pd.DataFrame(data['ten'])
    sheet4Frame.to_excel(writer, 'bottom10Percent' + sheetName, index=False)
    sheet5Frame = pd.DataFrame(data['twenty'])
    sheet5Frame.to_excel(writer, 'bottom20Percent' + sheetName, index=False)

    return

# analyze incoming article if it's a CSV
def analyzeCSV(dataFile):

    articles = []

    clickThrough = 0
    clicks = 0
    articleViewCount = 0
    impressions = 0
    avgRanking = 0.0

    csv_file = pd.read_csv(dataFile)

    #perform various calculations / averages
    for i, row in csv_file.iterrows():

        dataObject = eval(row.to_json().replace('null', "'N/A'"))
        clickThrough += float(dataObject['CTR'].replace('%', ''))
        clicks += dataObject['Clicks']
        impressions += dataObject['Impressions']
        avgRanking += dataObject['Position']
        if dataObject['Impressions'] > 0:
            articleViewCount += 1

        articles.append(dataObject)

    length = len(articles)

    avgClicks = int(clicks / length)
    avgVisitors = int(impressions / length)
    avgRanking = int(avgRanking / length)
    avgCTR = (clickThrough / length)

    bestClick, worstClick = sortKey(articles, 'Clicks', False, 'Pages')
    bestVisit, worstVisit = sortKey(articles, 'Impressions', False, 'Pages')
    bestRank, worstRank = sortKey(articles, 'Position', True, 'Pages')

    filename = dataFile.replace(".csv", "")
    #generate overview sheet
    writer = pd.ExcelWriter(filename + '_Analyzed.xlsx')
    sheet1 = {}
    sheet1['avgClicks'] = [avgClicks]
    sheet1['avgVisitors'] = [avgVisitors]
    sheet1['avgRanking'] = [avgRanking]
    sheet1['avgCTR'] = [avgCTR]
    sheet1['totalClicks'] = [clicks]
    sheet1['totalImpressions'] = [impressions]
    sheet1Frame = pd.DataFrame(data=sheet1)
    sheet1Frame.to_excel(writer, 'Overall Article Statistics', index=False)

    allSheetFrame = pd.DataFrame(articles)
    allSheetFrame.to_excel(writer, 'All Articles', index=False)

    writeBestSheets(writer, 'ByClicks', bestClick)
    writeBestSheets(writer, 'ByVisits', bestVisit)
    writeBestSheets(writer, 'ByRank', bestRank)

    writeWorstSheets(writer, 'ByClicks',  worstClick)
    writeWorstSheets(writer, 'ByVisits',  worstVisit)
    writeWorstSheets(writer, 'ByRank', worstRank)

    writer.save()

    return

# analyze aritcle if it's an excel file
def analyzeXLSX(dataFile):

    articles = []

    exitRate = 0.0
    bounceRate = 0.0
    timeOnPage = 0.0
    uVisitors = 0
    entrances = 0
    articleViewCount = 0


    excel_file = pd.read_excel(dataFile, 'Dataset1')

    # perform various calculations and averages
    for i, row in excel_file.iterrows():

        dataObject = eval(row.to_json().replace('null', "'N/A'"))
        dataObject['Page'] = dataObject['Page'].replace("\\", "")

        if dataObject['Page'] != 'N/A':

            exitRate += dataObject['% Exit']
            bounceRate += dataObject['Bounce Rate']
            uVisitors += dataObject['Unique Pageviews']
            timeOnPage += dataObject['Avg. Time on Page']
            entrances += dataObject['Entrances']
            if dataObject['Pageviews'] > 0:
                articleViewCount += dataObject['Pageviews']

            articles.append(dataObject)

    length = len(articles)

    avgExitRate = (exitRate / length)
    avgBounceRate = (bounceRate / length)
    avgTimeOnPage = (timeOnPage / length)
    avgUVistors = (uVisitors / length)
    avgViewCount = int(articleViewCount / length)
    avgEntrance = int(entrances / length)

    bestExit, worstExit = sortKey(articles, '% Exit', True, 'Page')
    bestBounce, worstBounce = sortKey(articles, 'Bounce Rate', True, 'Page')
    bestVisit, worstVisit = sortKey(articles, 'Unique Pageviews', False, 'Page')
    bestTime, worstTime = sortKey(articles, 'Avg. Time on Page', True, 'Page')

    filename = dataFile.replace(".xlsx", "")

    #generate overview sheet
    writer = pd.ExcelWriter(filename + '_Analyzed.xlsx')
    sheet1 = {}
    sheet1['avgExitRate'] = [avgExitRate]
    sheet1['avgBounceRate'] = [avgBounceRate]
    sheet1['avgTimeOnPage'] = [avgTimeOnPage]
    sheet1['avgUniqueVistors'] = [avgUVistors]
    sheet1['avgViews'] = [avgViewCount]
    sheet1['avgEntrances'] = [avgEntrance]
    sheet1['totalViews'] = [articleViewCount]
    sheet1['totalEntrances'] = [entrances]
    sheet1['totalUniqueVisitors'] = [uVisitors]
    sheet1Frame = pd.DataFrame(data=sheet1)
    sheet1Frame.to_excel(writer, 'Overall Article Statistics', index=False)

    allSheetFrame = pd.DataFrame(articles)
    allSheetFrame.to_excel(writer, 'All Articles', index=False)

    writeBestSheets(writer, 'ByExitRate', bestExit)
    writeBestSheets(writer, 'ByBounceRate', bestBounce)
    writeBestSheets(writer, 'ByTimeOnPage', bestTime)
    writeBestSheets(writer, 'ByUniqueVisitors', bestVisit)

    writeWorstSheets(writer, 'ByExitRate', worstExit)
    writeWorstSheets(writer, 'ByBounceRate', worstBounce)
    writeWorstSheets(writer, 'ByTimeOnPage', worstTime)
    writeWorstSheets(writer, 'ByUniqueVisitors', worstVisit)

    writer.save()

    return

#check if article exists
def doesArticleExist(article, articlesList):

    exists = False, None

    for i, a in enumerate(articlesList):
        if article == a['Page']:
            exists = True, i
            break

    return exists

#reformat excel file with duplicates and bad text
def formatExcel(dataFile):

    articles = []
    recapString = 'football-season-recap'
    imageString = 'dsc-jpg'
    imageString2 = 'image_'
    flashString = 'flashtalking/'
    collectionString = 'collection_'
    prefix = '/sports/football/'
    suffix = '.html'

    badArticles = 0
    duplicates = 0

    excel_file = pd.read_excel(dataFile, 'Dataset1')

    for i, row in excel_file.iterrows():

        dataObject = eval(row.to_json().replace('null', "'N/A'"))
        dataObject['Page'] = dataObject['Page'].replace("\\", "")
        if '/sports/football-' in dataObject['Page']:
            dataObject['Page'] = dataObject['Page'][:dataObject['Page'].index('/sports/football-') + len('/sports/football-')].replace('-', '/') + \
                                 dataObject['Page'][dataObject['Page'].index('/sports/football-') + len('/sports/football-'):]

        if recapString not in dataObject['Page'] and imageString \
                       not in dataObject['Page'] and collectionString \
                       not in dataObject['Page'] and dataObject['Page'] != 'N/A' \
                                                 and imageString2 \
                       not in dataObject['Page'] and flashString \
                       not in dataObject['Page'] and suffix in dataObject['Page']:


            articles.append(dataObject)

        else:
            badArticles += 1

    reducedArticles = []

    for a in articles:

        print(a['Page'])

        clean = a['Page']

        clean = clean[clean.index(prefix):clean.index(suffix) + len(suffix)]
        articleExists, position = doesArticleExist(clean, reducedArticles)

        if articleExists:
            reducedArticles[position]['Pageviews'] += a['Pageviews']
            reducedArticles[position]['Unique Pageviews'] += a['Unique Pageviews']
            reducedArticles[position]['Avg. Time on Page'] = (reducedArticles[position]['Avg. Time on Page'] + a['Avg. Time on Page']) / 2
            reducedArticles[position]['Entrances'] += a['Entrances']
            duplicates += 1

        else:
            reducedArticles.append(a)

    pdb.set_trace()
    writer = pd.ExcelWriter(str(dataFile).replace('.xlsx', '') + '_REFORMATED.xlsx')
    sheet1Frame = pd.DataFrame(reducedArticles)
    sheet1Frame.to_excel(writer, 'Dataset1', index=False)
    writer.save()

    print(str(badArticles) + ' bad articles removed.')
    print(str(duplicates) + ' duplicates found and updated')

    return

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--filename', required=True)
    parser.add_argument('-r', '--reformat', required=False)
    args = parser.parse_args()

    dataFile = args.filename
    unformattedArticle = args.reformat

    if unformattedArticle:
        formatExcel(dataFile)

    else:

        ext = dataFile.split('.')[-1]

        if ext == 'csv':
            analyzeCSV(dataFile)
        elif ext == 'xlsx':
            analyzeXLSX(dataFile)
        else:
            print('Data file must be of .csv or .xlsx extension')
            exit(1)

    return

if __name__ == "__main__":
    main()