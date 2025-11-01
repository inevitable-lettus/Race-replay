import pandas as pd
import numpy as np
import math
from pathlib import Path

# Create sample_race directory
Path("sample_race").mkdir(exist_ok=True)

print("Generating sample race data...")

# ============ TRACK GENERATION (FIRST - BEFORE ANYTHING USES IT) ============
print("✓ Generating track waypoints...")

track_waypoints = []

# Bottom straight (left to right)
for i in range(20):
    t = i / 20.0
    x = t * 100
    y = 0
    track_waypoints.append((x, y))

# Right turn (top-right curve)
for i in range(20):
    angle = (i / 20.0) * math.pi
    x = 100 + 30 * math.sin(angle)
    y = 30 * (1 - math.cos(angle))
    track_waypoints.append((x, y))

# Top straight (right to left)
for i in range(20):
    t = i / 20.0
    x = 100 - t * 100
    y = 60
    track_waypoints.append((x, y))

# Left turn (bottom-left curve)
for i in range(20):
    angle = (i / 20.0) * math.pi
    x = 0 - 30 * math.sin(angle)
    y = 60 - 30 * (1 - math.cos(angle))
    track_waypoints.append((x, y))

# Close the loop
track_waypoints.append(track_waypoints[0])

print(f"  Generated {len(track_waypoints)} waypoints")

# ============ 1. STARTING GRID ============
print("\n✓ Creating starting_grid.csv...")
grid_data = {
    'Driver': ['Hamilton', 'Verstappen', 'Norris', 'Sainz'],
    'DriverName': ['Lewis Hamilton', 'Max Verstappen', 'Lando Norris', 'Carlos Sainz'],
    'Team': ['Mercedes', 'Red Bull', 'McLaren', 'Ferrari'],
    'GridPosition': [1, 2, 3, 4],
    'TyreCompound': ['Medium', 'Soft', 'Medium', 'Soft']
}
grid_df = pd.DataFrame(grid_data)
grid_df.to_csv('sample_race/starting_grid.csv', index=False)
print(grid_df)

# ============ 2. TELEMETRY ============
print("\n✓ Creating telemetry.csv...")

telemetry_data = []
frames = 500  # Longer race: 50 seconds
drivers = ['Hamilton', 'Verstappen', 'Norris', 'Sainz']

start_positions = {
    'Hamilton': 0,
    'Verstappen': 10,
    'Norris': 20,
    'Sainz': 30
}

np.random.seed(42)
for frame in range(frames):
    session_time = frame * 0.1  # 0.1 seconds per frame
    
    for driver in drivers:
        # Speed varies per driver
        speed_factor = 1.0 if driver == 'Hamilton' else 0.97 if driver == 'Verstappen' else 0.95 if driver == 'Norris' else 0.92
        
        # FASTER MOVEMENT: drivers move around track quickly
        waypoint_distance = (start_positions[driver] + session_time * 2.0 * speed_factor) % len(track_waypoints)
        
        wp_idx = int(waypoint_distance)
        wp_next = (wp_idx + 1) % len(track_waypoints)
        local_t = waypoint_distance - wp_idx
        
        x0, y0 = track_waypoints[wp_idx]
        x1, y1 = track_waypoints[wp_next]
        
        x = x0 + (x1 - x0) * local_t
        y = y0 + (y1 - y0) * local_t
        
        x += np.random.normal(0, 0.3)
        y += np.random.normal(0, 0.3)
        
        # Pit stop for Sainz at 15-20 seconds (frames 150-200)
        in_pit = 150 <= frame <= 200 and driver == 'Sainz'
        if in_pit:
            x, y = 10, 5
        
        telemetry_data.append({
            'SessionTime': session_time,
            'Driver': driver,
            'Lap': 1 + int((start_positions[driver] + session_time * 2.0 * speed_factor) / len(track_waypoints)),
            'X': x,
            'Y': y,
            'Speed': 210 if not in_pit else 0,
            'Throttle': 0.85 if not in_pit else 0.0,
            'Brake': 0.0 if not in_pit else 0.5,
            'Gear': 5 if not in_pit else 0,
            'inPit': in_pit
        })

tele_df = pd.DataFrame(telemetry_data)
tele_df.to_csv('sample_race/telemetry.csv', index=False)
print(f"Generated {len(tele_df)} telemetry records")
print(f"Race duration: {tele_df['SessionTime'].max():.1f} seconds")

# ============ 3. PIT STOPS ============
print("\n✓ Creating pit_stops.csv...")
pits_data = [
    {
        'SessionTime': 15.0,
        'Driver': 'Sainz',
        'Lap': 2,
        'PitTimeIn': 15.0,
        'PitTimeOut': 20.0,
        'StopDuration': 5.0,
        'OldCompound': 'Soft',
        'NewCompound': 'Medium'
    }
]
pits_df = pd.DataFrame(pits_data)
pits_df.to_csv('sample_race/pit_stops.csv', index=False)
print(pits_df)

# ============ 4. RACE EVENTS ============
print("\n✓ Creating race_events.csv...")
events_data = [
    {'SessionTime': 0.0, 'Lap': 0, 'Type': 'Start', 'Message': 'GREEN FLAG'},
    {'SessionTime': 5.0, 'Lap': 1, 'Type': 'Driver', 'Message': 'Hamilton leads'},
    {'SessionTime': 15.0, 'Lap': 2, 'Type': 'PitStop', 'Message': 'Sainz pits'},
    {'SessionTime': 20.0, 'Lap': 2, 'Type': 'PitStop', 'Message': 'Sainz out'},
    {'SessionTime': 30.0, 'Lap': 3, 'Type': 'Race', 'Message': 'GREEN FLAG'},
    {'SessionTime': 50.0, 'Lap': 5, 'Type': 'End', 'Message': 'END'},
]
events_df = pd.DataFrame(events_data)
events_df.to_csv('sample_race/race_events.csv', index=False)
print(events_df)

# ============ 5. LEADERBOARD ============
print("\n✓ Creating leaderboard.csv...")
leaderboard_data = []
times_and_orders = [
    (0.0, ['Hamilton', 'Verstappen', 'Norris', 'Sainz']),
    (10.0, ['Hamilton', 'Verstappen', 'Norris', 'Sainz']),
    (15.0, ['Hamilton', 'Verstappen', 'Norris', 'Sainz']),
    (25.0, ['Hamilton', 'Verstappen', 'Sainz', 'Norris']),
    (50.0, ['Hamilton', 'Verstappen', 'Sainz', 'Norris']),
]

for session_time, order in times_and_orders:
    for pos, driver in enumerate(order, 1):
        leaderboard_data.append({
            'SessionTime': session_time,
            'Position': pos,
            'Driver': driver,
            'GapAhead': 0.0 if pos == 1 else pos * 0.5,
            'Interval': 0.0 if pos == 1 else 0.5
        })

lb_df = pd.DataFrame(leaderboard_data)
lb_df.to_csv('sample_race/leaderboard.csv', index=False)
print(f"Generated {len(lb_df)} leaderboard entries")

# ============ 6. TRACK MAP ============
print("\n✓ Creating track_map.csv...")
track_data = {
    'X': [w[0] for w in track_waypoints],
    'Y': [w[1] for w in track_waypoints]
}
track_df = pd.DataFrame(track_data)
track_df.to_csv('sample_race/track_map.csv', index=False)
print(f"Track map: {len(track_df)} waypoints")
print(track_df.head(10))

print("\n✅ All sample data generated in ./sample_race/")
print("\nFiles created:")
print("  - starting_grid.csv (4 drivers)")
print("  - telemetry.csv (500 frames = 50 seconds)")
print("  - pit_stops.csv (Sainz pit at 15s)")
print("  - race_events.csv")
print("  - leaderboard.csv")
print("  - track_map.csv (81 waypoints = smooth oval)")
print("\nNow run: python main.py")
