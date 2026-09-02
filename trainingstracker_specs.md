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
 

Updates post phase 3:

Frontend reviews:
	- keep the dark touch and add purple details to the frontend, without overdo		ing 

Functional reviews:
 	- if an workout isn't marked as finished, meaning the user didn't finish 	and the auto finnish after 6 hours hasn't been reached, the user should be 	 able to resume that unfinished workout, if e.g the has been closed	
	- a panel showing the current workoutplan 
	- a 'last session' strip showing info about the last workout (date, days since, what it was, ...)
 	- the 'active plan' panel doesn't deserve it's own row - the option of switch should be implemented later on in 'workout plans'
	- a comfortable way of marking a workout as missed - surprise me.
	- in the training log: mark the current body weight at the time of each w		orkout
	  
