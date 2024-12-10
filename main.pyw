import time
import atexit
import os
import sys
import threading
import json
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from pypresence import Presence
from pystray import MenuItem as item, Icon, Menu
from PIL import Image
from notifypy import Notify
import irsdk

notification = Notify()

# Default settings
interval = 1
display_idle = True
display_github = True
EnableLock = False
CustomIdleText = "Idle"

# Settings
startup_errors = []  # List messages, show on startup notification.
try:
    settings_file = "settings.json"
    with open(settings_file, "r") as json_file:
        settings = json.load(json_file)
    interval = settings.get("updateInterval", interval)
    display_idle = settings.get("displayIdle", display_idle)
    display_github = settings.get("displayGithub", display_github)
    EnableLock = settings.get("EnableLock", EnableLock)
    CustomIdleText = settings.get("CustomIdleText", CustomIdleText)
except FileNotFoundError:  # create new settings.json
    with open(settings_file, "w") as json_file:
        settings = {
            "updateInterval": interval,
            "displayIdle": display_idle,
            "displayGithub": display_github,
            "EnableLock": EnableLock,
            "CustomIdleText": CustomIdleText,
        }
        json.dump(settings, json_file, indent=4)
        print(
            "Settings file not found, creating new settings file with default settings."
        )
        startup_errors.append(
            "Settings file not found. Created new file with default settings."
        )
except Exception as e:
    print(f"Error loading settings: {e}, resorting to default settings")
    startup_errors.append(f"Error loading settings, resorting to default settings.")


# EnableLock function
try:  # Psutil is optional to avoid unnecessary package installations
    import psutil

    psutil_installed = True
except ImportError:
    psutil_installed = False

lock_file = "irpc.lock"
if EnableLock:
    if psutil_installed:
        try:
            if os.path.isfile(lock_file):
                with open(lock_file, "r") as f:
                    pid = int(f.read())

                if psutil.pid_exists(pid):
                    print("iRacing Discord Rich Presence is already running.")
                    notification.title = "iRacing Rich Presence"
                    notification.message = "iRacing Discord Rich Presence is already running, if this is a mistake check the lock file."
                    notification.icon = "assets/logo.png"
                    notification.send()
                    sys.exit()
                else:  # Remove previous lock file if the PID does not match
                    os.remove(lock_file)

            with open(lock_file, "w") as f:
                f.write(str(os.getpid()))

        except Exception as e:
            print(f"Error creating or trying to access lock file: {e}")
            startup_errors.append("An error happened with the lock file.")
    else:  # Resort to just checking if the lock file exists.
        try:
            if os.path.isfile(lock_file):
                print("iRacing Discord Rich Presence is already running.")
                notification.title = "iRacing Rich Presence"
                notification.message = "iRacing Discord Rich Presence is already running, if this is a mistake check the lock file."
                notification.icon = "assets/logo.png"
                notification.send()
                sys.exit()
            else:
                with open(lock_file, "w") as f:
                    f.write(
                        "iRacing Discord Rich Presence lock file. This will be deleted on exit.\n"
                        "If this still exists after closing the script, delete it manually."
                    )
        except Exception as e:
            print(f"Error creating or trying to access lock file: {e}")
            startup_errors.append(f"An error happened with the lock file.")

stop_event = threading.Event()

# iRacing SDK
irsdk_obj = irsdk.IRSDK()
irsdk_obj.startup()

# Discord RPC setup
client_id = "1260920089486692413"  # Don't change this unless you have your own application set up
RPC = Presence(client_id)
RPC.connect()

initial_total_time = None


# Updating the RPC
def update_presence():

    while not stop_event.is_set():
        try:
            if irsdk_obj.is_initialized and irsdk_obj.is_connected:
                state = irsdk_obj["WeekendInfo"]["EventType"]
                lap_num = irsdk_obj["Lap"]
                car_idx = irsdk_obj["DriverInfo"]["DriverCarIdx"]
                carname = irsdk_obj["DriverInfo"]["Drivers"][car_idx][
                    "CarScreenNameShort"
                ]
                session_num = irsdk_obj["SessionNum"]
                session_info = irsdk_obj["SessionInfo"]["Sessions"][session_num]
                sessiontype = session_info["SessionType"]
                total_laps = session_info["SessionLaps"]
                if total_laps in ["unlimited", None, "None", 0]:
                    total_laps = None
                elapsed_time = irsdk_obj["SessionTime"]
                total_time = irsdk_obj["SessionTimeRemain"]
                best_lap = irsdk_obj["LapBestLapTime"]

                if total_time:
                    initial_total_time = total_time + elapsed_time

                display_total_time = (
                    initial_total_time if initial_total_time else total_time
                )
                position = (
                    irsdk_obj["PlayerCarPosition"] or "--"
                )  # If no position is set, display P--
                track = irsdk_obj["WeekendInfo"]["TrackDisplayName"]

                if total_laps is None:
                    if total_time in [None, "None", 604800] or state in [
                        "Test",
                        "Practice",
                    ]:
                        elapsed_time = time.strftime(
                            "%H:%M:%S", time.gmtime(elapsed_time)
                        )
                        statetext = f"{elapsed_time} | {lap_num} laps | {carname}"
                    elif state == "Time Attack":  # Time Attack enhancements
                        best_lap = time.strftime("%H:%M:%S", time.gmtime(best_lap))
                        statetext = f"Best Lap: {best_lap} | {lap_num} laps | {carname}"
                    else:
                        elapsed_time = time.strftime(
                            "%H:%M:%S", time.gmtime(elapsed_time)
                        )
                        display_total_time = time.strftime(
                            "%H:%M:%S", time.gmtime(display_total_time)
                        )
                        statetext = f"P{position} | {elapsed_time} of {display_total_time} | {carname}"
                else:
                    statetext = f"P{position} | {lap_num} of {total_laps} laps | {carname}"

                if display_github:  # changed in settings.json
                    largetexttext = "https://github.com/BananaJeanss/iRacingRPC"
                else:
                    largetexttext = "iRacing"

                if sessiontype == state:
                    details = f"{state} | {track}"
                elif state == "Time Attack":
                    details = f"{state} | {track}"
                else:
                    details = f"{state} - {sessiontype} | {track}"

                RPC.update(
                    state=statetext,
                    details=details,
                    large_image="iracing",
                    large_text=largetexttext,
                )
            elif display_idle:
                if display_github:
                    largetexttext = "https://github.com/BananaJeanss/iRacingRPC"
                else:
                    largetexttext = "iRacing"
                RPC.update(
                    details=CustomIdleText or "Idle",
                    large_image="iracing",
                    buttons=[  # Buttons tend to not appear on discord, unless you're hovering your mouse over a voice channel or are on mobile.
                        {
                            "label": "View on GitHub",
                            "url": "https://github.com/BananaJeanss/iRacingRPC",
                        }
                    ],
                )

            else:
                RPC.clear()
        except KeyError as e:
            print(f"Data not available from iRacing: {e}")
        except Exception as e:
            print(f"Error updating presence: {e}")

        stop_event.wait(interval)


# iRacing Status check
def iracing_status_check():
    while not stop_event.is_set():
        if not irsdk_obj.is_initialized or not irsdk_obj.is_connected:
            irsdk_obj.shutdown()
            irsdk_obj.startup()
        time.sleep(5)


# Quit function
quitstate = 0  # 0 if not quitting via tray, 1 if quitting via tray preventing atexit from running


def on_quit(icon):
    global quitstate
    quitstate = 1
    RPC.close()
    stop_event.set()
    icon.stop()
    if os.path.exists(lock_file):
        os.remove(lock_file)
    print("iRPC has closed successfully")
    notification.title = "iRacing Rich Presence"
    notification.message = "iRPC Closing"
    notification.icon = "assets/logo.png"
    notification.send()


def exit_handler():
    if quitstate == 0:
        on_quit(icon)


atexit.register(exit_handler)


# Tray Icons
def set_interval(new_interval):
    global interval
    interval = new_interval


def settings_window():
    def settings_thread():
        settings = tk.Tk()
        settings.title("iRacing RPC Settings")
        try:
            settings.iconbitmap("main.ico")
        except Exception as e:
            print(f"Error loading icon: {e}")
        settings.geometry("400x300")
        settings.resizable(False, False)

        # Styling
        style = ttk.Style()
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("TEntry", font=("Segoe UI", 10))
        style.configure("TCheckbutton", font=("Segoe UI", 10))

        settings_frame = ttk.Frame(settings, padding=20)
        settings_frame.pack(fill=tk.BOTH, expand=True)

        interval_label = ttk.Label(settings_frame, text="Update interval (seconds):")
        interval_label.pack(pady=5)
        interval_entry = ttk.Entry(settings_frame)
        interval_entry.insert(0, interval)
        interval_entry.pack(pady=5)

        custom_idle_label = ttk.Label(settings_frame, text="Custom Idle Text:")
        custom_idle_label.pack(pady=5)
        custom_idle_entry = ttk.Entry(settings_frame)
        custom_idle_entry.insert(0, CustomIdleText)
        custom_idle_entry.pack(pady=5)

        display_idle_var = tk.BooleanVar(value=display_idle)
        display_github_var = tk.BooleanVar(value=display_github)
        lock_file_var = tk.BooleanVar(value=EnableLock)

        display_idle_checkbutton = ttk.Checkbutton(
            settings_frame, text="Display idle text", variable=display_idle_var
        )
        display_idle_checkbutton.pack(pady=5)

        display_github_checkbutton = ttk.Checkbutton(
            settings_frame, text="Display GitHub Link", variable=display_github_var
        )
        display_github_checkbutton.pack(pady=5)

        lock_file_checkbutton = ttk.Checkbutton(
            settings_frame, text="Enable Lock File", variable=lock_file_var
        )
        lock_file_checkbutton.pack(pady=5)


        def save_settings():
            try:
                # Update the settings after saving.
                global interval, display_idle, display_github, CustomIdleText
                interval = int(interval_entry.get())
                display_idle = display_idle_var.get()
                display_github = display_github_var.get()
                CustomIdleText = custom_idle_entry.get()
                EnableLock = lock_file_var.get()
                new_settings = {
                    "updateInterval": interval,
                    "displayIdle": display_idle,
                    "displayGithub": display_github,
                    "CustomIdleText": CustomIdleText,
                    "EnableLock": EnableLock
                }
                # Write to settings.json
                with open(settings_file, "w") as json_file:
                    json.dump(new_settings, json_file, indent=4)
                messagebox.showinfo("Success", "Settings saved successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Error saving settings: {e}")

        save_button = ttk.Button(settings_frame, text="Save", command=save_settings)
        save_button.pack(pady=20)
        settings.mainloop()

    threading.Thread(target=settings_thread).start()


try:
    icon_image = Image.open("main.ico")
except FileNotFoundError:
    print("Icon file not found.")
    startup_errors.append("Icon file not found.")
    icon_image = None

icon = Icon("iRacingRP", icon_image, "iRacing Discord Rich Presence")
menu_items = [item("Settings", lambda: settings_window()), item("Quit", on_quit)]

icon.menu = Menu(*menu_items)

# Threads
presence_thread = threading.Thread(target=update_presence)
presence_thread.daemon = True
presence_thread.start()
status_thread = threading.Thread(target=iracing_status_check)
status_thread.daemon = True
status_thread.start()

# Run
notification.title = "iRacing Rich Presence"
if startup_errors:  # If there are any startup errors, display them in the notification.
    notification.message = (
        " ".join(startup_errors)
        + " Running in system tray, right click to access settings."
    )
else:
    notification.message = "Running in system tray, right click to access settings."
notification.icon = "assets/logo.png"

notification.send()
print("iRacing Discord Rich Presence is running")
icon.run()
