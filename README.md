This is a python script for extracting data from Fitocracy from the activities feed, and turning it into JSON format which can then be imported into a MongoDB database. Not a web-scraping script: you need to grab the HTML manually and pass it to the script. 

Fitocracy does provide a means of exporting data in the form of CSV files but there are a few problems with this:
1. They only do it on a per-exercise basis, which means downloading one file for each different exercise manually (which for me was 93 files) and then concatenating them.
2. Internally Fitocracy have changed some design decisions regarding how to store certain data, which makes it inconsistent (e.g. "time" changed between being stored in seconds, minutes and hours). They have also changed the ID system, meaning there is a large chunk of data where you cannot discern the exercise order for a given workout.
3. The CSV files don't contain information pertaining to personal records, comments, etc
4. The CSV files don't give units for weights and distances (though you can get them by parsing the "text" field)

Eventually I decided that since the data was correctly preserved in the feed when you visit the site, it would be easier to just parse that.


### Prerequisites
* Python3
* [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/)


### Usage
1. First go to https://www.fitocracy.com/profile/YOURUSERNAME/?activities and scroll down repeatedly until all of the workouts are loaded (it only loads 15 at a time so this may take a while)
2. Using developer tools, select the workout list and look for a div with class="activity-stream-content"
3. Right click, copy element, and paste into a text file
4. Run the script with:  
`python3 fitoparse.py INPUT_FILE_PATH [OUTPUT_FILE_PATH]`  
Where INPUT_FILE_PATH is the path to the file you copied the HTML into. If no output file path is given it will use output.json in the same directory that the script is placed in
5. You can then import it to a MongoDB database with:  
`mongoimport --db [DATABASE_NAME] --collection [COLLECTION_NAME] --file [PATH_TO_JSON_FILE] --jsonArray`


### Caveats
1. All fitocracy specific stuff is ignored, namely points, "props" and comments from other users (your own comments are kept though
2. Fitocracy allows you to group multiple exercises together within a single workout, this ignores such grouping and instead merges the exercise into one "group" per workout
3. This should work on most exercises but I have only actually tested it on the exercises I have performed in the past


### Example output
Turns this:
```
Shaun tracked a workout on 26 Jan, 2020:
    
    Cycling:
        00:25:00 | 4.3 mi | 160 BPM | light hills
    headwind!

    Squats:
        15 kg x 15
        80 kg x 5
        100 kg x 10

    Push-Up:
        20 reps (PR)
        
    --------------
        Your-user-name: The squats were easy but didn't have time to do too many
        Your-user-name: Oh a PR on the push-ups, sweet!
        Some-other-user: Nice workout!
```
into:
```json
{
    "date": {
        "$date": "2020-01-26T00:00:00Z"
    },
    "workout_id": 1,
    "exercises": [
        {
            "exercise_id": 1,
            "type": "cardio",
            "name": "Cycling",
            "sets": [
                {
                    "set_id": 1,
                    "time": 1560,
                    "distance": {"value": 4.3, "unit": "miles"},
                    "avhr": 160,
                    "other": "light hills"
                }
            ],
            "exercise_comment": "headwind!"
        },
        {
            "exercise_id": 2,
            "type": "weights",
            "name": "Squats",
            "sets": [
                {
                    "set_id": 1,
                    "weight": {"value": 15, "unit": "kg"},
                    "reps": 15
                },
                {
                    "set_id": 2,
                    "weight": {"value": 80, "unit": "kg"},
                    "reps": 5
                },
                {
                    "set_id": 3,
                    "weight": {"value": 100, "unit": "kg"},
                    "reps": 10
                }
            ]
        },
        {
            "exercise_id": 3,
            "type": "bodyweight",
            "name": "Push-Up",
            "sets": [
                {
                    "set_id": 1,
                    "reps": 20,
                    "pr": true
                }
            ]
        }
    ],
    "workout_comments": "The squats were easy but didn't have time to do too many \n\n Oh a PR on the push-ups, sweet!"
}
```
(except without the whitespace)
