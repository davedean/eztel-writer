I notice we store these in the csv

Format	LMUTelemetry v2
Version	1
Player	Dean Davids
TrackName	Algarve International Circuit
CarName	The Bend Team WRT 2025 #31:LM
SessionUTC	2025-11-18T13:52:51Z
LapTime [s]	302.325043
TrackLen [m]	0.00
GameVersion	1.0
Event	Practice


Issues:

1) Track Name, doesn't include variant / layout ?
2) CarName, that's the team name or something? I would like to store the car/variant/model instead, we can store Team Name but I don't think it's important
3) TrackLen is 0?
4) No sectors? If they are a "track level" datum, we should store them.

I also notice in the "data" section we have this (I manually / randomly selected lines):

LapDistance [m]	LapTime [s]	Sector [int]	Speed [km/h]	EngineRevs [rpm]	ThrottlePercentage [%]	BrakePercentage [%]	Steer [%]	Gear [int]	X [m]	Y [m]	Z [m]
260.344	302.325	0	0.00	1740.59	0.00	61.26	-1.63	4	-238.31	-12.60	307.05
882.076	302.325	0	100.07	5042.36	2.65	0.00	-15.82	2	-95.69	-3.23	393.17
2867.300	302.325	0	145.60	5911.45	99.68	0.00	-4.97	3	294.79	1.65	-192.26
3685.692	302.325	0	178.11	5906.33	98.96	0.00	4.90	4	291.71	-0.97	-539.25
4621.737	302.325	0	246.43	5944.07	100.00	0.00	0.47	6	-170.52	-8.78	52.92

Issues:

5) So we store the laptime on every tick? We don't need to do that.
6) Sector is empty? Why store sector every tick?
7) we store elevation? I don't think we need it?






