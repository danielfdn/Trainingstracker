Specifications for the 'trainingstracker'

Basic functionalities:
	- Manage exercises & workoutplans via CRUD  
	- user can select one (!) active workoutplan
	- user can start a workout, tracking total workout time, date and while wor-		king out, the user can enter all his sets for all exercises
	- the user can review his workout history via a seperate training-log. 
		working as a seperate endpoint, offering two views - the first view 		    shows all past workouts, the second offers a analysis of past workou		ts, in monthly chunks. It shows the user which exercises have which 		    progress comparing to selected months. E.g: Progress: 09/25 vs 04/26
 	- the application won't be public and won't need an auth. 

Endpoints:
NOTE: Those endpoints aren't the total amount of endpoints but should give you a vague idea of the navigation for the Product I thought of
	
	- '/' Landing page, serving the feature selecting a user-profile
	- '/"user"' e.g -> '/tom' main option menu, with:
		- creating workoutplans
		- selecting active workoutplan
		- entering the training-log
		- starting a workout
		- edit user data


Frontend:
	- The frontend should have a dark, minimalistic style
	- frontend should have a well usable UI for Desktop as well as Mobile
	- React, TS on vite & Tailwind as the Tech stack of choice
 

	
