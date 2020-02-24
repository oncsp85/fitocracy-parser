import sys
from datetime import datetime
import json
import requests


def read_tokens(input_file_path):
	''' 
	Read the file where the access_token is kept, and check if it is still 
	valid. If not call refresh_tokens() to get a new one.
	'''
	with open(input_file_path, "r") as file:
		token_obj = json.loads(file.read())
	if datetime.now() > datetime.fromtimestamp(int(token_obj["expires_at"])):
		token_obj = refresh_tokens(token_obj, input_file_path)
	return token_obj


def refresh_tokens(token_obj, file_path):
	'''
	Request new tokens from Strava and update the file.
	'''
	CLIENT_ID = "CENSORED"
	CLIENT_SECRET = "CENSORED"
	refresh_token = token_obj["refresh_token"]
	url = (
		f"https://www.strava.com/oauth/token?"
		f"client_id={CLIENT_ID}&"
		f"client_secret={CLIENT_SECRET}&"
		f"refresh_token={refresh_token}&"
		f"grant_type=refresh_token"
	)
	response = requests.post(url, headers={"Accept": "application/json"}).json()
	for k in response.keys():
		token_obj[k] = response[k]
	with open(file_path, "w") as file:
		file.write(json.dumps(token_obj, indent=4))
	return token_obj


def get_activities(access_token):
	'''
	Grab all activities from Strava and convert them to a dictionary
	'''
	page = 1
	url = (
		f"https://www.strava.com/api/v3/athlete/activities?"
		f"access_token={access_token}&"
	  	f"before=&after=&"   # These both take UNIX timestamps
	  	f"per_page=100&page="
	)
	activities = []
	while True:
		response = requests.get(
				url + str(page), headers={"Accept": "application/json"})
		activity_list = response.json()
		if len(activity_list) != 0:
			activities += activity_list
			page += 1
		else:
			break
	# Return them in ascending date order
	return sorted(activities, key=lambda l: l["start_date"])


def build_dictionary(activities):
	'''
	With the aforementioned dictionary, pick out the data that I need and put 
	it into a new dictionary that has the same structure as my database.
	This will merge all activities on the same day into different sets of the 
	same workout.
	'''
	names = {
		"Ride": "Cycling", 
		"Run": "Running", 
		"VirtualRide": "Cycling (stationary)"
	}
	current_date = ""
	current_workout = {}
	workouts = []
	for activity in activities:
		if activity["start_date"][:10] != current_date:
			current_date = activity["start_date"][:10]
			if current_workout != {}:
				workouts.append(current_workout)
			current_workout = {
				"workout_id": 1,
				"date": {"$date": f"{current_date}T00:00:00Z"},
				"exercises": []
			}
		name = names[activity["type"]]
		# See if there is already an exercise with the same name
		for exercise in current_workout["exercises"]:
			# If there is, use it and grab the last set_id used
			if exercise["name"] == name:
				current_exercise = exercise
				set_id = exercise["sets"][-1]["set_id"] + 1
				break
		else:
			# If there isn't already an exercise with the same name, make one
			current_exercise = {
				"exercise_id": len(current_workout["exercises"]) + 1,
				"type": "cardio",
				"name": name,
				"sets": []
			}
			current_workout["exercises"].append(current_exercise)
			set_id = 1
		# Either way, make a new set and append it to the set list
		current_set = {
			"set_id": set_id,
			"distance": {
				"value": int(activity["distance"]) / 1609,
				"unit": "mi"
			},
			"time": activity["moving_time"]
		}
		if activity["has_heartrate"]:
			current_set["avhr"] = activity["average_heartrate"]
		current_exercise["sets"].append(current_set)
	workouts.append(current_workout)
	return workouts


def main():
	if len(sys.argv) == 2:
		input_file_path = sys.argv[1]
	else:
		print("Expected argument: filepath to JSON file containing Strava tokens")
		return

	# Get the access token for authentication
	access_token = read_tokens(input_file_path)["access_token"]
	# Get a list of my activities from Strava
	activities = get_activities(access_token)
	# Convert each Strava activity into the format I need
	workouts = build_dictionary(activities)
	# Write the JSON file
	with open("strava_ouput.json", "w") as file:
		file.write(json.dumps(workouts))

if __name__ == "__main__":
	main()