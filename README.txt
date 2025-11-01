race_replay_project/
│
├── data_centre.py       # Load, parse, provide race data
├── animation.py         # Race, leaderboard, messages animation code
└── main.py              # Entry point, interface, connecting animation and data_centre

Data_centre - 
Sorting, formatting and cleaning data to be used for animation. 
Sorting includes arranging events in chronological order according to the race timeline. 
Formatting includes setting up said timeline.
Cleaning includes fixing empty data points or finding mistakes in data collection

The timeline is then projected onto a graph which updates according to frequency (normally set at 30 frames per second). 

A leaderboard and race messages update according to data provided. 

The goal is to be able to use the interface for any sort of race - car, drone, bike, go-karts. 
As long as the data recorded is accurate and according to instructions. 


