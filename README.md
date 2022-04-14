# abundat_rs

## Installation
The required dependencies for the projects are noted in an `environment.yaml` file.
Please make sure to update the `environment.yaml` while installing a new library.

To install the packages to root environment, 

```shell
conda env update -n root -f environment.yml
```

## Testing
The code could be tested on your local computer after checking out the git repo.
Please use the `customer_test` customer to test your stuff. There are few basic end to end tests that would
be used to validate the changes when a PR is raised or merged to `Prod_Test` branch or `Test` branch.

It is not extensive and very basic and the plan is in the future to add more test cases and
actually have test case for each of the new functionality developed.

The tests are run automatically through `circleci`

The test server runs backdated articles ( 60 days) from the current day daily.

## Deployment

Deployment is done automatically through `circle_ci`. 

#### Test System Changes:
Always make changes by creating a new branch of Prod_Test. Make sure to test it and then 
raise a PR for review and merging it to `Prod_Test` branch.

Any changes made on the `Prod_Test` branch will be pushed to the test server.
 
#### Prod System Changes: 
Any changes made on the `master` branch will be pushed to
the Prod server.

While moving changes from test to Prod, please make sure to create a separate branch out of
master and then pull the changes from `Prod_Test` to the newly created branch. 
**Please do not merge changes directly from `Prod_Test` to `master`**

The configurations are different from Prod and Test and please make sure to promote the conf
changes that should be promoted to Prod.

### Supervisor
The processes are monitored through supervisord and the configuration for the same is present in the `supervisord` directory.
Currently there are 2 processes monitored by the supervisor, `scheduler` and `alert`.

`scheduler` is the core process and `alert` is the one which consumes the alerts sent by the supervisord and sends email or
skype message.

The log files for `supervisord` and `alert` are found in the `logs` directory under
`supervisor.log` and `alert.log` respectively.

To Run Supervisord with a specific conf file

```shell
supervisord -c supervisord.conf
```

The following commands should be followed for starting, stopping and checking the status of an individual app.


`supervisorctl start scheduler`
`supervisorctl stop scheduler`
`supervisorctl status all`


```shell
supervisorctl reread
supervisorctl update
supervisorctl restart - restarts all the processes monitored by supervisor
```

#### Macro - what's happening?
We get data from a company called Scorestream.  They crowd-source sports scores.  We use an API to hook into their database 
where we then get data, save it, sort it, add color to it, and publish articles about it.

80% of our time is spent sorting data and getting organized, and 20% is spent actually writing the articles.

We built this so that it's flexible.  If we want to add more sports we can because all games are the same.  
There is a winning team, losing team, home team and away team.  One team wins or loses or both teams tie, but other than 
that things happen during the game.  No matter if it's innings and runs, quarters and points or periods and goals, we can 
report on a big win as a big win and a close game as a close game.

We have different market areas that we work in, and while we will need to really work on these in the near future, 
our current way of doing it has allowed us to learn quickly.


##### Sample Content

https://www.richlandsource.com/sports/football/too-much-punch-london-blackjacks-taft/article_3b4bc194-59cc-52ca-b8a7-08781c624e0c.html - this has a headline, lead (the first sentence) and L3 (stands for level 3 which is bad namingn I know but I couldn't come up with anything better) data.

https://www.richlandsource.com/sports/football/stopped-cold-waterford-thwarts-berne-union-s-quest/article_8d5a6139-d1a4-5a0c-97ab-7054bc4384fe.html - this only has a headline and lead.  Either the box score was bad (it had a negative value, didn't have high enough confidence, or somethign else happened that hit our QA flags in the L3 section to kill the last 3 sentences)

https://www.richlandsource.com/sports/football/mccomb-pours-it-on-patrick-henry/article_ea8e843b-d420-5ac5-b1e2-d8e2a55a8490.html - this is a full article with a L2_Rules (lead + headline) + L3_Data (what happened during each quarter)

## How does it all fit together?

* `Scheduler` schedules an article write job with the date, customer name and the flag for fetching
data from scorestream.
        
* The `ai_article_handler` processes the following steps.
    * creates a `customer_config` object by fetching the data from the `customer_config.json` for the appropriate
    customer name
    * calculates the date range for which the games have to be fetched.
    * If the `fetch_games` flag is set to `True`, fetches the games from scorestream api and massages them before
    uploading it to the database.
    * Scans the `dynamodb` for all games played between the date range.
    * Applies `game_filter` on those games with the input from the customer config, 
    like squad level, state ,sports etc.
    * Now the `filtered_games` are passed on to the next stage for writing articles
* The `write_one_article` function in `article_write` module does the following
    * Create a `AllGameData` object which consists of 
        * SportDetails fetched from sports_config.
        * Team details - both away and home team data fetched from `RS_TEAM` table.
        * L2_Data.
            * Determines the article code like if its a shutout win, competetive win, close win etc by 
            analyzing the box scores and overall game data.
            * Picks out a selective random content and headline from the list of the available
            templates.
        * L3_Data
            * Analyzes the box scores and gives text sentence templates for each key_period.
    * The articles templates are then passed through `article_output` which makes appropriate
      replacements for the keywords, produces article output in various formats as defined.
    * The articles are written to the file by default but also could be published to various
      output endpoints like CMS, Wordpress and plenty to come.
* Finally , the articles are sent as file to the email addresses stated in the config. A threshold alert email is
  also sent if the publishing threshold falls below a certain threshold.
  
## Key Web Links

    https://www.scorestream.com/api/docs - API documentation for our vendor.  This also has a sample for what our most used method (recommended.broadcast.games.search) outputs.  I recommend spending time with this.
    
    https://www.richlandsource.com/sports/football - this is where our articles output.  They're the articles without photos just slightly down the page.
    
    https://www.richlandsource.com/tncms/webservice/#howto - this is documentation for the BLOX API hook-in.
    
ANY TIME YOU ARE USING RS_SPORTS_WRITE.PY MAKE BLOX=FALSE. BLOX=TRUE WILL AUTO-PUBLISH THE ARTICLE¶


## Miscellanous
To copy the packages to the root environment.
```shell
conda env update -n root -f environment.yml
```

To Install Supervisord for Py3k.

```shell
pip install git+https://github.com/Supervisor/supervisor
```