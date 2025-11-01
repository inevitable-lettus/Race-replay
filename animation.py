import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSlider, 
                             QTableWidget, QTableWidgetItem, QSplitter)

from PyQt6.QtCore import Qt, QTimer
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except ImportError:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
import numpy as np 

"""ANIMATION CLASS"""

class RaceWindow(QMainWindow):
    
    def __init__(self, data_centre):
        super().__init__()
        self.data_centre = data_centre
        self.setWindowTitle("Race window")
        self.setGeometry(100, 100, 1200, 800)
        self.race_data = None
        self.timeline = None
        self.current_frame = 0
        self.is_playing = False

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)  # Corrected method connection
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
        panel = QWidget()
        layout = QVBoxLayout(panel)

        #create matplotlib figure and canvas
        self.figure = Figure(figsize=(10, 8), facecolor='#1e1e1e')
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        #configure the plot
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
        
        #Race time display
        self.time_label = QLabel("Race Time: 00:00.000")
        self.time_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; padding: 10px; "
            "background-color: #2d2d2d; color: white; border-radius: 5px;"
        )
        layout.addWidget(self.time_label)

        #leadeboard section
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
        """)  # Ensure this is a single statement
        
        layout.addWidget(self.leaderboard_table)
        
        #Race messages section 
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
        
        #Play/Pause button
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
        """)  # Ensure this is a single statement
        controls_layout.addWidget(self.play_button)
        
        #Reset button
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
        
        #speed control
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

        #Timeline slider
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
    

    """PLAYBACK CONTROLS"""

    def toggle_play(self):
        if self.is_playing:
            self.pause()
        else:
            self.play()  # Changed from self.start() to self.play()
    
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
        
        # Redraw track outline if available
        if self.track_x is not None and self.track_y is not None:
            self.ax.plot(self.track_x, self.track_y, 
                        color='white', linewidth=2, alpha=0.5, label='Track')
        
        # Check if we have position data
        if 'x' not in frame_data.columns or 'y' not in frame_data.columns:
            self.ax.set_title("Track Map (No position data)", color='white')
            self.canvas.draw()
            return
            
        # Get positions
        x_positions = frame_data['x'].values
        y_positions = frame_data['y'].values
        
        # Get pit status for color coding
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
            
            # Plot driver position
            self.ax.scatter(x, y, c=color, s=150, alpha=0.9, 
                          edgecolors='white', linewidth=2, zorder=10)
            
            # Add driver label
            self.ax.text(x, y + 5, str(driver), 
                       fontsize=9, fontweight='bold',
                       ha='center', va='bottom', color='white',
                       bbox=dict(boxstyle='round,pad=0.3', 
                               facecolor=color, alpha=0.7, edgecolor='none'))
        
        # Reconfigure plot
        self.ax.set_aspect('equal')  # Corrected method name
        self.ax.set_facecolor('#2d2d2d')
        self.ax.set_title("Track Map", fontsize=16, fontweight='bold', color='white')
        self.ax.set_xlabel("X Position (m)", color='white')
        self.ax.set_ylabel("Y Position (m)", color='white')
        self.ax.tick_params(colors='white')
        self.ax.grid(True, alpha=0.2, color='white')
        
        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#3498db', label='On Track'),
            Patch(facecolor='#e74c3c', label='In Pit')
        ]
        self.ax.legend(handles=legend_elements, loc='upper right', 
                      facecolor='#1e1e1e', edgecolor='white', 
                      labelcolor='white', framealpha=0.9)
        
        # Render the canvas
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