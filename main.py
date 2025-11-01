import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QMessageBox,
    QStackedWidget, QSplitter, QTableWidget, QTableWidgetItem, QSlider
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from pathlib import Path
import pandas as pd
import numpy as np

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except ImportError:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Import your data_centre
from data_centre import DataCentre, Race_timeline


class DataInputWidget(QWidget):
    """File input screen with 6 file pickers"""
    def __init__(self, parent=None, default_dir="./sample_race"):
        super().__init__(parent)
        self.default_dir = default_dir
        self.edits = {}
        self.main_window = parent
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("📁 Load Race Data Files"))
        
        # File rows
        files = [
            ("Starting Grid", "grid", "starting_grid.csv"),
            ("Telemetry", "telemetry", "telemetry.csv"),
            ("Pit Stops", "pits", "pit_stops.csv"),
            ("Race Events", "events", "race_events.csv"),
            ("Leaderboard", "leaderboard", "leaderboard.csv"),
            ("Track Map", "track", "track_map.csv")
        ]
        
        for label_text, key, placeholder in files:
            row = QHBoxLayout()
            row.addWidget(QLabel(label_text + ":"))
            ed = QLineEdit()
            ed.setPlaceholderText(f"{self.default_dir}/{placeholder}")
            self.edits[key] = ed
            row.addWidget(ed, 1)
            
            btn = QPushButton("Browse")
            btn.clicked.connect(lambda checked, k=key: self._browse(k))
            row.addWidget(btn)
            lay.addLayout(row)
        
        # Buttons
        btn_row = QHBoxLayout()
        fill_btn = QPushButton("Fill Sample Paths")
        fill_btn.clicked.connect(self._fill_sample)
        btn_row.addWidget(fill_btn)
        
        self.load_btn = QPushButton("Load & Start Race")
        self.load_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        self.load_btn.clicked.connect(self._load_data)
        btn_row.addWidget(self.load_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)
        
        # Status
        self.status = QLabel("Select files and click 'Load & Start Race'")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("padding: 10px; background: #f0f0f0; border-radius: 5px;")
        lay.addWidget(self.status)
        lay.addStretch()

    def _browse(self, key):
        start_dir = str(Path(self.default_dir).resolve())
        path, _ = QFileDialog.getOpenFileName(self, f"Select {key}", start_dir, "CSV (*.csv)")
        if path:
            self.edits[key].setText(path)

    def _fill_sample(self):
        base = Path(self.default_dir).resolve()
        mapping = {
            "grid": base / "starting_grid.csv",
            "telemetry": base / "telemetry.csv",
            "pits": base / "pit_stops.csv",
            "events": base / "race_events.csv",
            "leaderboard": base / "leaderboard.csv",
            "track": base / "track_map.csv"
        }
        for k, p in mapping.items():
            self.edits[k].setText(str(p))

    def _load_data(self):
        # Collect paths
        paths = {k: ed.text().strip() for k, ed in self.edits.items()}
        
        # Check all filled
        missing = [k for k, v in paths.items() if not v]
        if missing:
            QMessageBox.warning(self, "Missing Files", f"Please select: {', '.join(missing)}")
            return
        
        # Check files exist
        for k, p in paths.items():
            if not Path(p).exists():
                QMessageBox.critical(self, "File Not Found", f"Cannot find: {p}")
                return
        
        self.status.setText("Loading data...")
        QApplication.processEvents()
        
        # Load into DataCentre
        dc = DataCentre()
        success = dc.load_data(
            paths["grid"], paths["telemetry"], paths["pits"],
            paths["events"], paths["track"], paths["leaderboard"]
        )
        
        if not success:
            QMessageBox.critical(self, "Load Error", "Failed to load data. Check console for errors.")
            self.status.setText("Load failed.")
            return
        
        # Build timeline
        try:
            rt = Race_timeline(dc)
            race_df = rt.stitch_data()
            
            if race_df.empty:
                QMessageBox.warning(self, "No Data", "Stitched race data is empty.")
                return
            
            self.status.setText(f"Loaded {len(race_df)} frames. Starting race...")
            
            # Pass to race window
            if self.main_window:
                self.main_window.start_race(dc, rt, race_df)
                
        except Exception as e:
            QMessageBox.critical(self, "Processing Error", f"Error building timeline:\n{e}")
            self.status.setText("Processing failed.")


class RaceWindow(QMainWindow):
    """Full race animation window with Matplotlib and controls"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Race Replay")
        self.setGeometry(100, 100, 1200, 800)
        
        self.data_centre = None
        self.race_timeline = None
        self.race_data = None
        self.timeline = None
        self.current_frame = 0
        self.is_playing = False
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.fps = 30
        self.playback_speed = 1.0
        
        self.track_x = None
        self.track_y = None
        
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_panel = self.create_track_panel()
        splitter.addWidget(left_panel)
        
        right_panel = self.create_info_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([1000, 400])
        main_layout.addWidget(splitter)
        
        controls = self.create_controls()
        main_layout.addLayout(controls)

    def create_track_panel(self):
        """Create matplotlib track visualization panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Create matplotlib figure and canvas
        self.figure = Figure(figsize=(10, 8), facecolor='#1e1e1e')
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        # Configure the plot
        self.ax.set_facecolor('#1e1e1e')
        self.ax.set_aspect('equal')
        self.ax.set_title("Track Map", fontsize=16, fontweight='bold', color='white')
        self.ax.set_xlabel("X Position (m)", color='white')
        self.ax.set_ylabel("Y Position (m)", color='white')
        self.ax.tick_params(colors='white')
        self.ax.grid(True, alpha=0.2, color='white')
        
        layout.addWidget(self.canvas)
        return panel
    
    def create_info_panel(self):
        """Create the right panel with leaderboard and race messages"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Race time display
        self.time_label = QLabel("Race Time: 00:00.000")
        self.time_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; padding: 10px; "
            "background-color: #2d2d2d; color: white; border-radius: 5px;"
        )
        layout.addWidget(self.time_label)
        
        # Leaderboard section
        leaderboard_label = QLabel("📊 Leaderboard")
        leaderboard_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; margin-top: 15px; color: white;"
        )
        layout.addWidget(leaderboard_label)
        
        # Create leaderboard table
        self.leaderboard_table = QTableWidget()
        self.leaderboard_table.setColumnCount(3)
        self.leaderboard_table.setHorizontalHeaderLabels(["Pos", "Driver", "Status"])
        
        # Set column widths
        self.leaderboard_table.setColumnWidth(0, 50)   # Position
        self.leaderboard_table.setColumnWidth(1, 120)  # Driver name
        self.leaderboard_table.setColumnWidth(2, 100)  # Status
        
        # Style the table
        self.leaderboard_table.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #444;
                gridline-color: #444;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                color: white;
                padding: 5px;
                border: 1px solid #444;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        layout.addWidget(self.leaderboard_table)
        
        # Race messages section
        messages_label = QLabel("📢 Race Control")
        messages_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; margin-top: 15px; color: white;"
        )
        layout.addWidget(messages_label)
        
        # Race message display
        self.message_label = QLabel("GREEN FLAG")
        self.message_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 15px; "
            "background-color: #27ae60; color: white; border-radius: 8px;"
        )
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label)
        
        # Add stretch to push everything to top
        layout.addStretch()
        
        return panel
    
    def create_controls(self):
        """Create the bottom control panel"""
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        
        # Play/Pause button
        self.play_button = QPushButton("▶ Play")
        self.play_button.clicked.connect(self.toggle_play)
        self.play_button.setFixedWidth(120)
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #229954;
            }
        """)
        controls_layout.addWidget(self.play_button)
        
        # Reset button
        reset_button = QPushButton("⟲ Reset")
        reset_button.clicked.connect(self.reset_animation)
        reset_button.setFixedWidth(100)
        reset_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #5dade2;
            }
        """)
        controls_layout.addWidget(reset_button)
        
        # Speed control
        speed_label = QLabel("Speed:")
        speed_label.setStyleSheet("color: white; font-size: 14px; margin-left: 20px;")
        controls_layout.addWidget(speed_label)
        
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(10)
        self.speed_slider.setValue(5)  # Default 1.0x
        self.speed_slider.setFixedWidth(150)
        self.speed_slider.valueChanged.connect(self.update_speed)
        controls_layout.addWidget(self.speed_slider)
        
        self.speed_value_label = QLabel("1.0x")
        self.speed_value_label.setStyleSheet("color: white; font-size: 14px; min-width: 50px;")
        controls_layout.addWidget(self.speed_value_label)
        
        # Add flexible space
        controls_layout.addStretch()
        
        # Timeline slider
        timeline_label = QLabel("Timeline:")
        timeline_label.setStyleSheet("color: white; font-size: 14px;")
        controls_layout.addWidget(timeline_label)
        
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setMinimum(0)
        self.timeline_slider.setMaximum(1000)
        self.timeline_slider.setValue(0)
        self.timeline_slider.sliderMoved.connect(self.seek_frame)
        self.timeline_slider.setMinimumWidth(300)
        controls_layout.addWidget(self.timeline_slider)
        
        # Frame counter
        self.frame_label = QLabel("0 / 0")
        self.frame_label.setStyleSheet("color: white; font-size: 14px; min-width: 80px;")
        controls_layout.addWidget(self.frame_label)
        
        return controls_layout
    
    # ============ PLAYBACK CONTROLS ============
    
    def toggle_play(self):
        """Toggle between play and pause"""
        if self.is_playing:
            self.pause()
        else:
            self.play()
    
    def play(self):
        """Start the animation"""
        if self.race_data is None:
            return
        
        self.is_playing = True
        self.play_button.setText("⏸ Pause")
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #f39c12;
            }
        """)
        
        # Calculate timer interval based on FPS and speed
        interval = int(1000 / (self.fps * self.playback_speed))
        self.timer.start(interval)

    def pause(self):
        """Pause the animation"""
        self.is_playing = False
        self.play_button.setText("▶ Play")
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        self.timer.stop()
        
    def reset_animation(self):
        """Reset animation to beginning"""
        self.current_frame = 0
        self.timeline_slider.setValue(0)
        self.pause()
        self.update_display()
    
    def update_speed(self, value):
        """Update playback speed based on slider"""
        # Convert slider value (1-10) to speed multiplier (0.2x - 2.0x)
        self.playback_speed = value / 5.0
        self.speed_value_label.setText(f"{self.playback_speed:.1f}x")
        
        # Update timer interval if playing
        if self.is_playing:
            interval = int(1000 / (self.fps * self.playback_speed))
            self.timer.setInterval(interval)
            
    def seek_frame(self, value):
        """Jump to a specific frame in the timeline"""
        self.current_frame = value
        self.update_display()
        
    def update_frame(self):
        """Advance to next frame (called by timer)"""
        if self.race_data is None or self.timeline is None:
            return
        
        # Move to next frame
        self.current_frame += 1
        
        # Loop back to start if reached end
        if self.current_frame >= len(self.timeline):
            self.current_frame = 0
        
        # Update slider position
        self.timeline_slider.setValue(self.current_frame)
        
        # Redraw everything
        self.update_display()
        
    def update_display(self):
        """Update all visual elements for current frame"""
        if self.race_data is None or self.timeline is None:
            return
        
        if self.current_frame >= len(self.timeline):
            return
        
        # Get current time point
        current_time = self.timeline[self.current_frame]
        
        # Get all data for this time point
        try:
            frame_data = self.race_data.loc[current_time]
        except KeyError:
            print(f"Warning: No data for time {current_time}")
            return
        
        # Update each component
        self.update_time_display(current_time)
        self.update_track(frame_data)
        self.update_leaderboard(frame_data)
        self.update_message(frame_data)
        self.update_frame_counter()
        
    def update_time_display(self, current_time):
        """Update the race time label"""
        total_seconds = current_time.total_seconds()
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        self.time_label.setText(f"⏱ Race Time: {minutes:02d}:{seconds:06.3f}")

    def update_track(self, frame_data):
        """Update track visualization with driver positions"""
        self.ax.clear()
    
        # IMPORTANT: Set aspect ratio and limits FIRST before plotting
        self.ax.set_aspect('equal', adjustable='box')
    
    # Set axis limits based on track
        if self.track_x and self.track_y:
            self.ax.set_xlim(min(self.track_x) - 10, max(self.track_x) + 10)
            self.ax.set_ylim(min(self.track_y) - 10, max(self.track_y) + 10)
        else:
            self.ax.set_xlim(-20, 150)
            self.ax.set_ylim(-20, 100)
    
        # Draw track outline FIRST
        if self.track_x is not None and self.track_y is not None and len(self.track_x) > 1:
            self.ax.plot(self.track_x, self.track_y, 
                        color='white', linewidth=3, alpha=0.7, label='Track', zorder=1)
            # Fill track area (optional)
            self.ax.fill(self.track_x, self.track_y, color='#1a1a1a', alpha=0.3, zorder=0)
    
        # Check if we have position data
        if 'x' not in frame_data.columns or 'y' not in frame_data.columns:
            self.ax.set_title("Track Map (No position data)", color='white', fontsize=16, fontweight='bold')
            self.ax.set_facecolor('#2d2d2d')
            self.ax.tick_params(colors='white')
            self.canvas.draw()
            return
    
        # Get positions and pit status
        x_positions = frame_data['x'].values
        y_positions = frame_data['y'].values
        in_pit_status = frame_data.get('inPit', pd.Series([False] * len(frame_data)))
    
        # Plot each driver
        for idx, driver in enumerate(frame_data.index):
            x = x_positions[idx]
            y = y_positions[idx]
        
            # Skip if position is NaN
            if pd.isna(x) or pd.isna(y):
                continue
        
            # Color: red if in pit, blue if racing
            color = '#e74c3c' if in_pit_status.iloc[idx] else '#3498db'
        
            # Plot driver position as a larger circle
            self.ax.scatter(x, y, c=color, s=200, alpha=0.95, 
                        edgecolors='white', linewidth=2, zorder=10, marker='o')
        
            # Add driver label above the circle
            self.ax.text(x, y + 3, str(driver)[:3], 
                        fontsize=10, fontweight='bold',
                        ha='center', va='bottom', color='white',
                        bbox=dict(boxstyle='round,pad=0.4', 
                                facecolor=color, alpha=0.8, edgecolor='white', linewidth=1))
    
        # Configure plot appearance
        self.ax.set_facecolor('#2d2d2d')
        self.ax.set_title("Track Map", fontsize=16, fontweight='bold', color='white')
        self.ax.set_xlabel("X Position (m)", color='white', fontsize=12)
        self.ax.set_ylabel("Y Position (m)", color='white', fontsize=12)
        self.ax.tick_params(colors='white', labelsize=10)
        self.ax.grid(True, alpha=0.2, color='white', linestyle='--')

        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#3498db', edgecolor='white', label='On Track'),
            Patch(facecolor='#e74c3c', edgecolor='white', label='In Pit')
        ]
        self.ax.legend(handles=legend_elements, loc='upper right', 
                      facecolor='#1e1e1e', edgecolor='white', 
                      labelcolor='white', framealpha=0.95, fontsize=10)

        # Make sure everything is visible
        self.canvas.draw()
    
    def update_leaderboard(self, frame_data):
        """Update the leaderboard table"""
        # Sort by position if available
        if 'Position' in frame_data.columns:
            sorted_data = frame_data.sort_values('Position')
        else:
            sorted_data = frame_data
        
        # Set number of rows
        self.leaderboard_table.setRowCount(len(sorted_data))
        
        # Populate table
        for row, (driver, data) in enumerate(sorted_data.iterrows()):
            # Position number
            pos_item = QTableWidgetItem(str(row + 1))
            pos_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.leaderboard_table.setItem(row, 0, pos_item)
            
            # Driver name
            driver_item = QTableWidgetItem(str(driver))
            self.leaderboard_table.setItem(row, 1, driver_item)
            
            # Status
            in_pit = data.get('inPit', False)
            status = "🔴 PIT" if in_pit else "🟢 Racing"
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.leaderboard_table.setItem(row, 2, status_item)
        
    def update_message(self, frame_data):
        """Update race control message display"""
        # Get message from first row (same for all drivers)
        if 'message' in frame_data.columns and len(frame_data) > 0:
            message = str(frame_data['message'].iloc[0]).upper()
        else:
            message = "GREEN"
        
        self.message_label.setText(message)
        
        # Color code based on message type
        if "GREEN" in message or message == "":
            bg_color = "#27ae60"  # Green
        elif "YELLOW" in message or "VSC" in message:
            bg_color = "#f39c12"  # Yellow/Orange
        elif "RED" in message or "SC" in message or "SAFETY CAR" in message:
            bg_color = "#e74c3c"  # Red
        else:
            bg_color = "#95a5a6"  # Gray
        
        self.message_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; padding: 15px; "
            f"background-color: {bg_color}; color: white; border-radius: 8px;"
        )
        
    def update_frame_counter(self):
        """Update frame counter label"""
        if self.timeline is not None:
            total_frames = len(self.timeline)
            self.frame_label.setText(f"{self.current_frame} / {total_frames}")
    
    def load_race_data(self, data_centre, race_timeline, race_df):
        """Called by main window after data loads"""
        self.data_centre = data_centre
        self.race_timeline = race_timeline
        self.race_data = race_df
        
        # Create timeline from race_df index
        self.timeline = race_df.index.get_level_values('Time').unique().tolist()
        
        # Update timeline slider max
        self.timeline_slider.setMaximum(len(self.timeline) - 1)
        
        # Extract track
        track_map = data_centre.get_track_map()
        if track_map is not None and not track_map.empty:
            # Try common column names
            x_col = next((c for c in ['X', 'x', 'Xpos', 'Longitude'] if c in track_map.columns), None)
            y_col = next((c for c in ['Y', 'y', 'Ypos', 'Latitude'] if c in track_map.columns), None)
            
            if x_col and y_col:
                self.track_x = track_map[x_col].dropna().tolist()
                self.track_y = track_map[y_col].dropna().tolist()
        
        self.current_frame = 0
        self._update_display()

    def _update_display(self):
        """Internal call to update display (avoid method name conflict)"""
        self.update_display()


class MainWindow(QMainWindow):
    """Main application window with toggle between input and race"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Race Replay System")
        self.resize(1400, 900)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Toggle button
        self.toggle_btn = QPushButton("📊 Switch to Race View")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.toggled.connect(self._on_toggle)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #5dade2; }
            QPushButton:checked { background-color: #e67e22; }
        """)
        layout.addWidget(self.toggle_btn)
        
        # Stacked widget for screens
        self.stack = QStackedWidget()
        
        self.input_screen = DataInputWidget(parent=self, default_dir="./sample_race")
        self.stack.addWidget(self.input_screen)
        
        self.race_screen = RaceWindow(parent=self)
        self.stack.addWidget(self.race_screen)
        
        layout.addWidget(self.stack, 1)
        
        # Start on input
        self.stack.setCurrentWidget(self.input_screen)

    def _on_toggle(self, checked):
        if checked:
            self.stack.setCurrentWidget(self.race_screen)
            self.toggle_btn.setText("📁 Switch to Input View")
        else:
            self.stack.setCurrentWidget(self.input_screen)
            self.toggle_btn.setText("📊 Switch to Race View")

    def start_race(self, data_centre, race_timeline, race_df):
        """Called by input widget after successful load"""
        self.race_screen.load_race_data(data_centre, race_timeline, race_df)
        self.toggle_btn.setChecked(True)
        self.stack.setCurrentWidget(self.race_screen)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern look
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
