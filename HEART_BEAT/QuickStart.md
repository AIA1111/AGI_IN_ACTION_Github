The HEART_BEAT/ folder is designed as a reusable plugin.
   To use it in any other project:
                                                                                
  1. Copy the HEART_BEAT/ folder into the new project
  2. Edit only service_monitor.py — replace the service definitions (names,     
  ports, process names, paths, restart strategies)                            
  3. Update the .plist file with the correct python path and project path
  4. Update KILL_HEARTBEAT.command with the correct process names
  5. Update or rename "watchdog_agi.pid" and "/tmp/heartbeat_watchdog_agi.log" as per the project name

  Everything else (heartbeat_watchdog.py, heartbeat_manager.py, __init__.py) is
  generic and works as-is with any set of services.

  The lifecycle is:
  Double-click START_HEARTBEAT.command
      → Watchdog starts (nohup — survives Terminal close)
      → launchd job installed (survives reboot)
      → NEVER goes offline
      → Checks every 60 seconds
      → Auto-restarts any crashed service
      → Survives M3 reboot (launchd brings watchdog back → watchdog brings
  everything back)

  Double-click KILL_HEARTBEAT.command
      → launchd job removed (won't restart on reboot)
      → Watchdog killed
      → All services killed
      → Everything dead — stays dead

  That's the full concept — one click to make it immortal, one click to kill it.

