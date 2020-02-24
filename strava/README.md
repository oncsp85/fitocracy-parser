Between 20th February 2017 and 23rd January 2018, I stopped using Fitocracy. This was because I wasn't lifting at the time and my GPS watch was automatically uploading all of my cardio exercises to my Strava account, so I didn't feel it was necessary to duplicate this data. There are therefore a number of workouts that only appear on Strava and will thus be missed by the fitocracy feed parser. 

Luckily Strava has an API, so getting the data from there is much more straight-forward. I wrote a script to grab all of the exercises from Strava via the API between the above dates, and put them into the same data-structure as my database so that I could also import them. I've uploaded it here for posterity and to keep a record of it in case I need to remind myself how to use the Strava API again.


### Usage
1. Log in to Strava and go to https://www.strava.com/settings/api and make a new app, putting anything you want in the fields. Make a note of the `Client ID` and `Client Secret` fields that Strava then gives you.
2. In a browser, go to to https://www.strava.com/oauth/authorize?client_id=CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=SCOPE, where `CLIENT_ID` is the Client ID from step 1, and changing `SCOPE` to the required permissions:
	* `read` gives read access to all public data, except activities
	* `read_all` gives read access to non-public routes, segments and events
	* `profile:read_all` gives read access to non-public profile information
	* `activity:read` and `activity:read_all` give read access to public and non-public activity data respectively
	* `profile:write` and `activity:write` give write access for profiles and activities respectively
3. Click Authorize. You will be redirected to http://localhost with a bunch of options after it in the address bar, which of course won't load anything. One of the options is `code=SOMELONGHASH`: make a note of it.
4. Make a POST request (using cURL/Postman etc) to https://www.strava.com/oauth/token?client_id=CLIENT_ID&client_secret=CLIENT_SECRET&grant_type=authorization_code&code=CODE, where `CLIENT_ID` and `CLIENT_SECRET` are the value obtained from step 1, and `CODE` is the code obtained from step 3.
5. If it has worked you should end up with a JSON object starting `{ "token_type": "Bearer"...`, copy all of this text and paste it into a file. 
6. Edit lines 23&24 of `stravaapi.py` to add the `Client ID` and `Client Secret` values. If you only want to get activities from certain dates, edit line 49 accordingly. Save the changes.
7. Run `python3 stravaapi.py FILE` where `FILE` is the path to the file you made in step 5. It'll automatically check if the `authorization_code` is still valid, and if it isn't it'll request a new one from Strava and update the token file.
