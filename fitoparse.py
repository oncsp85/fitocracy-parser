import sys
from os import getcwd
from bs4 import BeautifulSoup
from datetime import datetime
import json


def parse_fitocracy_feed(input_path, output_path="output.json"):
	"""
	Takes the path to a file containing the HTML of a Fitocracy activities  
	feed, parses it using BeautifulSoup, extracts the information regarding the
	activities, adds it to a data structure and writes that to a JSON file.
	"""
	print("Parsing HTML...")
	with open(input_path) as input_file:
		soup = BeautifulSoup(input_file, features="html.parser")

	workout_list = soup.find_all(attrs={"data-ag-type":"workout"})
	# Workout order is newest -> oldest, change to oldest -> newest
	print(f"Parsed feed, found: {len(workout_list)} workouts")
	workout_list.reverse()
	parsed_workouts = []  # This is the root of the final data-structure

	#########  WORKOUT  #########
	current_date = ""
	for workout in workout_list:

		date_text = workout.find(attrs={"class":"action_time"}).string
		# Convert to the format required by MongoDB
		date_obj = datetime.strptime(date_text, "%d %b, %Y")
		date = {"$date": datetime.isoformat(date_obj) + "Z"}

		if date != current_date:
			current_date = date
			workout_id = 1
		parsed_workout = {
			"workout_id": workout_id, "date": date, "exercises": []
		}
		workout_id += 1
		
		#########  EXERCISE  #########
		exercise_list = workout.find_all(attrs={"class":"action_prompt"})
		ex_id = 1
		for exercise in exercise_list:
			name = exercise.string
			# Skip past any "groups" that have been found
			if name[1:6] == "Group":
				continue
			parsed_exercise = {"exercise_id": ex_id, "name": name, "sets": []}
			ex_id += 1

			#########  SET  #########
			set_list = exercise.next_sibling.next_sibling.find_all("li")
			set_id = 1
			for s in set_list:
				pr = False
				if s.has_attr("class") and "stream_note" in s["class"]:
					parsed_exercise["exercise_comment"] = s.text
				else:
					set_text = s.contents[0].strip(" \n")
					# Set was a PR (has extra text that needs removing)
					if s.has_attr("class") and "action_pr" in s["class"]:
						pr = True
						set_text = set_text[:-5].strip()
					set_obj = parse_set(set_text)
					parsed_exercise["type"] = set_obj.pop("type")
					set_obj["set_id"] = set_id
					if pr:
						set_obj["pr"] = True
					set_id += 1
					# Add the current set to the finished exercise
					parsed_exercise["sets"].append(set_obj)
			# Add the current exercise to the finished workout
			parsed_workout["exercises"].append(parsed_exercise)

		####  WORKOUT COMMENTS  ####
		# Filter out all comments left by other people
		comment_list = filter(
			lambda x: x.contents[0].strip() != "", 
			workout.find_all(class_="comment-copy-wrapper"))
		comments = [comment.find(class_="comment-copy").get_text().strip() 
			for comment in comment_list]
		# Merge multiple comments into 1, split with two line breaks.
		comments = "\n\n".join(comments)
		if len(comments) != 0:
			parsed_workout["workout_comments"] = comments

		# Add the current workout to the finished list of workouts
		parsed_workouts.append(parsed_workout)

	# Write the output file
	with open(output_path, "w") as output_file:
		output_file.write(json.dumps(parsed_workouts))


def parse_set(exercise):
	"""
	Determines what type of exercise the set refers to, and parses it 
	accordingly. Returns a dictionary containing information about the set.
	"""
	if ":" in exercise:
		# Cardio exercises uniquely contain ':' due to the time field.
		parsed_set = {"type": "cardio"}
		details = exercise.split(" | ")
		hours, mins, secs = map(int, details[0].split(":"))
		parsed_set["time"] = hours * 3600 + mins * 60 + secs
		if len(details) > 1:
			others = parse_other_cardio_details(details[1:])
			for k, v in others.items():
				if isinstance(v, tuple):
					parsed_set[k] = {"value": v[0], "unit": v[1]}
				else:
					parsed_set[k] = v
	else:
		# Weight-lifting exercise of the form e.g. "80 kg x 12"
		if "x" in exercise:
			parsed_set = {"type": "weights"}
			lift, reps = exercise.split(" x ")
			reps = reps.split(" ")[0]
			weight, unit = lift.split(" ")
			parsed_set["weight"] = {"value": float(weight), "unit": unit}
			if float(reps) == int(reps):
				reps = int(reps)
			else:
				reps = float(reps)
			parsed_set["reps"] = reps 		
		# Bodyweight exercise of the form e.g. "5 reps [| assisted | 5kg]"
		else:
			parsed_set = {"type": "bodyweight"}
			# A bodyweight exercise that's either weighted or assisted
			if "|" in exercise:
				split_reps = exercise.split(" | ")
				reps = split_reps[0][:-4]
				weight, unit = split_reps[2].split(" ")
				weight = float(weight)
				if split_reps[1] == "assisted":
					weight *= -1
			else:
				weight = 0
				reps = exercise[:-4]
			reps = float(reps)
			if int(reps) == float(reps):
				reps = int(reps)
			if weight != 0:
				parsed_set["weight"] = {"value": weight, "unit": unit}
			parsed_set["reps"] = reps
	return parsed_set


def parse_other_cardio_details(details):
	"""
	This is for parsing all optional data that comes after the "time" property 
	of cardio exercises. Works out what they are based on the unit and returns 
	a dictionary where the key is the property and the value is either a tuple 
	(value, unit), or just the value
	"""
	parsed_details = {}
	distance_units = ["km", "mi", "m", "ft", "yd"]
	speed_units = ["km/hr", "mph", "min/km", "min/mi", "split", "fps", "m/s"]
	for detail in details:
		value_units = detail.split(" ")
		if len(value_units) == 2:
			# is potentially a value/unit pair
			value, unit = value_units
			if unit in distance_units:
				parsed_details["distance"] = (float(value), unit)
			elif unit in speed_units:
				parsed_details["speed"] = (float(value), unit)
			elif unit == "BPM":
				parsed_details["avhr"] = (int(value), unit)
			elif unit in ["kg", "lb"]:
				parsed_details["weight"] = (float(value), unit)
			elif unit == "%":
				parsed_details["resistance"] = (int(value), unit)
			else:
				# Not a known unit, catch-all
				parsed_details["other"] = detail
		else:
			# Not a known unit, catch-all
			parsed_details["other"] = detail
	return parsed_details
	

def main():
	if not 1 < len(sys.argv) < 4:
		print("Error: At least one argument is required "
			"(the path to the input file).")
	else:
		FILE_PATH = sys.argv[1]
		if len(sys.argv) == 3:
			parse_fitocracy_feed(FILE_PATH, sys.argv[2])
		else:
			print(f"No output path given, will write to file "
				f"{getcwd()}/output.json")
			parse_fitocracy_feed(FILE_PATH)

if __name__ == "__main__":
	main()
