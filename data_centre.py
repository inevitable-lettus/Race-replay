# data_centre.py
import numpy as np
import pandas as pd

"""DATA CENTRE CLASS"""
class DataCentre:
    def __init__(self):
        self.starting_grid = None
        self.driver_telemetry = None
        self.driver_pits = None
        self.race_events = None
        self.track_map = None
        self.leaderboard_changes = None  # initialized to avoid attribute errors



    def load_data(self, grid_file, tele_file, pits_file, events_file, track_file, leaderboard_file):
        """Load data from csv files given by user"""
        try:
            self.starting_grid = pd.read_csv(grid_file)
            self.driver_telemetry = pd.read_csv(tele_file)
            self.driver_pits = pd.read_csv(pits_file)
            self.race_events = pd.read_csv(events_file)
            self.track_map = pd.read_csv(track_file)
            self.leaderboard_changes = pd.read_csv(leaderboard_file)
        except Exception as e:
            print(f"Error loading data: {e}")
            return None
        return True

    def check_data(self):
        loaded = []
        if self.starting_grid is not None:
            loaded.append("Starting grid")
        if self.driver_telemetry is not None:
            loaded.append("Driver telemetry")
        if self.driver_pits is not None:
            loaded.append("Driver pits")
        if self.race_events is not None:
            loaded.append("Race events")
        if self.track_map is not None:
            loaded.append("Track map")
        if self.leaderboard_changes is not None:
            loaded.append("Leaderboard changes")

        if loaded:
            print("Loaded datasets:", ", ".join(loaded))
        else:
            print("No data loaded")
        return None

    def _ensure_timedelta(self, df, col="SessionTime", unit="s"):
        """Convert SessionTime column to Timedelta robustly."""
        if col not in df.columns:
            return df
        try:
            # try numeric seconds first
            df[col] = pd.to_timedelta(df[col].astype(float), unit=unit)
        except Exception:
            # fallback to pandas parsing (handles 'HH:MM:SS', ISO, etc.)
            df[col] = pd.to_timedelta(df[col])
        return df

    def _interpolate_numeric(self, df):
        """Interpolate only numeric columns using time index (TimedeltaIndex)."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) == 0:
            return df
        df[numeric_cols] = df[numeric_cols].interpolate(method="time")
        return df

    def get_starting_grid(self):
        """Format starting grid data to be used for animation"""
        if self.starting_grid is None:
            return None
        #sort by grid position (if present)
        df = self.starting_grid.copy()
        if 'GridPosition' in df.columns:
            df = df.sort_values(by='GridPosition')
        #drop any rows with null values
        df = df.dropna().drop_duplicates()
        return df

    def get_driver_telemetry(self, drv):
        """Format driver telemetry data to be used for animation"""
        if self.driver_telemetry is None:
            return pd.DataFrame()
        #filter by driver
        df = self.driver_telemetry[self.driver_telemetry['Driver'] == drv].copy()
        df = self._ensure_timedelta(df, "SessionTime")
        if "SessionTime" in df.columns:
            df = df.set_index("SessionTime").sort_index()
            df = self._interpolate_numeric(df)
        df = df.drop_duplicates().dropna()
        return df

    def get_driver_pits(self, drv):
        """Format driver pits data to be used for animation"""
        if self.driver_pits is None:
            return pd.DataFrame()
        df = self.driver_pits[self.driver_pits['Driver'] == drv].copy()
        df = self._ensure_timedelta(df, "SessionTime")
        if "SessionTime" in df.columns:
            df = df.set_index("SessionTime").sort_index()
            df = self._interpolate_numeric(df)
        df = df.drop_duplicates().dropna()
        return df

    def get_race_events(self):
        """Format race events data to be used for animation"""
        if self.race_events is None:
            return pd.DataFrame()
        df = self.race_events.copy()
        df = self._ensure_timedelta(df, "SessionTime")
        if "SessionTime" in df.columns:
            df = df.set_index("SessionTime").sort_index()
            # events may not have numeric columns; interpolate only numeric
            df = self._interpolate_numeric(df)
        df = df.drop_duplicates().dropna()
        return df

    def get_leaderboardTimeline(self):
        if self.leaderboard_changes is None:
            return pd.DataFrame()
        df = self.leaderboard_changes.copy()
        df = self._ensure_timedelta(df, "SessionTime")
        if "SessionTime" in df.columns:
            df = df.set_index("SessionTime").sort_index()
            df = self._interpolate_numeric(df)
        df = df.drop_duplicates().dropna()
        return df
    
    def get_track_map(self):
        """Format track map data to be used for animation"""
        return self.track_map
    
    def get_RaceTimings(self):
        # Robustly find race duration, start (GREEN message) and end (END message)
        if self.race_events is None or 'SessionTime' not in self.race_events.columns:
            return None, None, None

        df = self.race_events.copy()
        df = self._ensure_timedelta(df, "SessionTime")
        # work on column values rather than index
        times = df['SessionTime']
        duration = times.max() - times.min()

        # message-based start/end (case-insensitive)
        if 'Message' in df.columns:
            msg = df['Message'].astype(str)
            start_mask = msg.str.contains("GREEN", case=False, na=False)
            end_mask = msg.str.contains("END", case=False, na=False)

            start_time = times[start_mask].min() if start_mask.any() else times.min()
            end_time = times[end_mask].max() if end_mask.any() else times.max()
        else:
            start_time = times.min()
            end_time = times.max()

        return duration, start_time, end_time
    
class Race_timeline:
    def __init__(self,data_centre):
            self.timeline = None
            self.data_centre = data_centre
            self.leaderboard = self.data_centre.get_leaderboardTimeline()
            self.events = self.data_centre.get_race_events()
            self.duration, self.start_time, self.end_time = self.data_centre.get_RaceTimings()
            self.track = self.data_centre.get_track_map()
            self.startingGrid = self.data_centre.get_starting_grid()
            
    def create_timeline(self):
            if self.start_time is None or self.end_time is None:
                return pd.TimedeltaIndex([])
            #create a timeline for the race
            self.timeline = pd.timedelta_range(start=self.start_time, end=self.end_time, freq='100ms')
            return self.timeline

    def teleAndPits(self):
        frames = []
        timeline = self.create_timeline()

        if self.startingGrid is None:
            return pd.DataFrame()

        # allow either 'Driver' or 'DriverName' in starting grid
        driver_col = 'Driver' if 'Driver' in self.startingGrid.columns else 'DriverName'
        for drv in self.startingGrid[driver_col]:
            tele = self.data_centre.get_driver_telemetry(drv)
            pits = self.data_centre.get_driver_pits(drv)
            if tele is None:
                tele = pd.DataFrame()
            if pits is None:
                pits = pd.DataFrame()
            # join on time index
            merged = tele.join(pits, how='outer', lsuffix='_tele', rsuffix='_pits')
            # suffix driver name to columns to avoid collisions
            merged.columns = [f"{col}_{drv}" for col in merged.columns]
            frames.append(merged)

        if not frames:
            return pd.DataFrame()
        timeline_df = pd.concat(frames, axis=1)
        # reindex to full timeline to ensure consistent time steps
        if len(timeline) > 0:
            timeline_df = timeline_df.reindex(timeline)
        return timeline_df


    def build_timeline(self):
        timeline = self.create_timeline()
        if self.leaderboard is None or len(timeline) == 0:
            return pd.DataFrame()
        # reindex leaderboard onto timeline (forward-fill)
        leaderboard = self.leaderboard.reindex(timeline, method='pad')
        return leaderboard
    
    #Stitch together all the data into a single multi-index dataframe fit for animation
    def stitch_data(self):
        # create canonical timeline
        timeline = self.create_timeline()
        if timeline is None or len(timeline) == 0:
            return pd.DataFrame()

        # get drivers from starting grid
        if self.startingGrid is None:
            return pd.DataFrame()
        driver_col = 'Driver' if 'Driver' in self.startingGrid.columns else 'DriverName'
        drivers = list(self.startingGrid[driver_col].astype(str))

        # build MultiIndex (Time, Driver)
        index = pd.MultiIndex.from_product([timeline, drivers], names=['Time', 'Driver'])
        df = pd.DataFrame(index=index)

        # prepare global message series (one value per time)
        if self.events is not None and 'Message' in self.events.columns:
            ev = self.events.copy().reindex(timeline, method='pad')
            message_series = ev['Message'].fillna('').astype(str)
        else:
            message_series = pd.Series([''] * len(timeline), index=timeline)

        # candidate position column names in telemetry
        x_candidates = ['X', 'x', 'Xpos', 'PosX', 'Longitude', 'Lon']
        y_candidates = ['Y', 'y', 'Ypos', 'PosY', 'Latitude', 'Lat']

        # iterate drivers and populate columns
        for drv in drivers:
            tele = self.data_centre.get_driver_telemetry(drv)
            pits = self.data_centre.get_driver_pits(drv)

            # reindex telemetry to timeline (prefer nearest within tolerance, else pad)
            if tele is not None and not tele.empty:
                try:
                    tele_re = tele.reindex(timeline, method='nearest', tolerance=pd.Timedelta('500ms'))
                except Exception:
                    tele_re = tele.reindex(timeline, method='pad')
            else:
                tele_re = pd.DataFrame(index=timeline)

            # find x/y column names
            x_col = next((c for c in x_candidates if c in tele_re.columns), None)
            y_col = next((c for c in y_candidates if c in tele_re.columns), None)

            # get position arrays (align by timeline)
            x_vals = tele_re[x_col] if x_col in tele_re.columns else pd.Series(index=timeline, dtype=float)
            y_vals = tele_re[y_col] if y_col in tele_re.columns else pd.Series(index=timeline, dtype=float)

            # reindex pits to timeline and derive boolean inPit
            if pits is not None and not pits.empty:
                try:
                    pits_re = pits.reindex(timeline, method='pad')
                except Exception:
                    pits_re = pits.reindex(timeline)
                pit_flag_col = next((c for c in ['InPit', 'inPit', 'Pit', 'PitStatus'] if c in pits_re.columns), None)
                if pit_flag_col:
                    in_pit = pits_re[pit_flag_col].fillna(False).astype(bool)
                else:
                    # any non-null value in a pit row counts as being in pit at that timestamp
                    in_pit = pits_re.notna().any(axis=1).reindex(timeline).fillna(False).astype(bool)
            else:
                in_pit = pd.Series(False, index=timeline, dtype=bool)

            # assign into MultiIndex DataFrame for this driver
            df.loc[(slice(None), drv), 'x'] = np.asarray(x_vals.reindex(timeline))
            df.loc[(slice(None), drv), 'y'] = np.asarray(y_vals.reindex(timeline))
            df.loc[(slice(None), drv), 'inPit'] = np.asarray(in_pit.reindex(timeline).fillna(False).astype(bool))

        # assign global message (same for all drivers at a given time)
        # index product order is (time, driver) so repeat each message len(drivers) times
        df['message'] = np.repeat(message_series.values, len(drivers))

        # optionally include duplicate Time and Driver columns (useful if you prefer columns)
        df['Time'] = df.index.get_level_values(0)
        df['Driver'] = df.index.get_level_values(1)

        # ensure dtypes are sensible
        df['inPit'] = df['inPit'].astype(bool)
        return df

