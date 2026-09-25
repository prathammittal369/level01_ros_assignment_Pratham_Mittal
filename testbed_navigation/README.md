# testbed_navigation

Manual, plugin-level Nav2 navigation stack for the **Testbed-T1.0.0** robot.
Instead of calling `nav2_bringup`, this package starts each `nav2` server /
plugin directly (`map_server`, `amcl`, `controller_server`, `planner_server`,
`behavior_server`, `bt_navigator`, `waypoint_follower`, `velocity_smoother`,
`collision_monitor`) from three independent, composable launch files.

## Package layout

```
testbed_navigation/
├── CMakeLists.txt
├── package.xml
├── config/
│   ├── amcl_params.yaml      # AMCL localization parameters
│   └── nav2_params.yaml      # controller / planner / behavior / bt_navigator /
│                              # waypoint_follower / velocity_smoother /
│                              # collision_monitor + local & global costmaps
├── launch/
│   ├── map_loader.launch.py   # map_server only
│   ├── localization.launch.py # map_server + amcl
│   └── navigation.launch.py   # localization + full nav2 control stack
└── rviz/
    └── nav2_default_view.rviz
```

## Design / approach

Each launch file only stands up the lifecycle nodes it owns, plus a
dedicated `nav2_lifecycle_manager` that `configure()`s and `activate()`s
exactly those nodes. This keeps every stage independently testable (per the
help.md guideline "Test Components Independently") while still letting
`navigation.launch.py` compose the whole stack with one command by
`Include`-ing `localization.launch.py`, which in turn brings up its own
`map_server` + `amcl`.

- **`map_loader.launch.py`** — starts `nav2_map_server` (managed by
  `lifecycle_manager_map_server`) against `testbed_bringup`'s
  `testbed_world.yaml`. Used to sanity-check that the map appears correctly
  in RViz before anything else is layered on top.
- **`localization.launch.py`** — starts its own `map_server` + `nav2_amcl`
  instance (managed together by `lifecycle_manager_localization`), using
  `config/amcl_params.yaml`. It is self-contained on purpose (it does not
  `Include` `map_loader.launch.py`) so both files can run a `map_server`
  under their own lifecycle manager without two managers fighting over the
  same node.
- **`navigation.launch.py`** — `Include`s `localization.launch.py`, then
  starts `controller_server` (DWB local planner), `planner_server` (NavFn
  global planner), `behavior_server` (spin / back up / drive-on-heading /
  wait recoveries), `bt_navigator` (stock
  `navigate_to_pose_w_replanning_and_recovery.xml` behavior tree),
  `waypoint_follower`, `velocity_smoother` and `collision_monitor`, all
  managed by `lifecycle_manager_navigation`, and finally opens RViz with a
  nav2-oriented view (map, costmaps, particle cloud, global plan, 2D Pose
  Estimate / Nav2 Goal tools).

### Velocity command chain

`controller_server` → `cmd_vel_nav` → `velocity_smoother` →
`cmd_vel_smoothed` → `collision_monitor` (stops the robot if its footprint
polygon detects an obstacle) → `cmd_vel` → the robot's diff-drive Gazebo
plugin. This mirrors the pattern used internally by `nav2_bringup`.

### Costmaps

`local_costmap` runs in the `odom` frame (rolling 4m×4m window) and
`global_costmap` runs in the `map` frame with a static layer seeded from
`map_server`. Both use an `obstacle_layer` fed by `/scan` plus an
`inflation_layer` sized for the robot's real footprint (~0.3 m radius,
derived from the caster/wheel offsets in `testbed.xacro`).

### Only basic functionality, on purpose

Per the assignment ("Only basic navigational functionality is expected"),
plugin choices were kept deliberately simple: NavFn (Dijkstra, no smoothing)
for global planning, DWB for local control, and just the four standard
recovery behaviors. No smac_planner, no regulated pure pursuit, no
keepout/speed filters.

## Usage

```bash
# 1) Bring up the simulated robot + world (from testbed_bringup)
ros2 launch testbed_bringup testbed_full_bringup.launch.py

# 2a) Sanity-check the map on its own
ros2 launch testbed_navigation map_loader.launch.py

# 2b) OR test localization on its own (starts its own map_server too)
ros2 launch testbed_navigation localization.launch.py

# 2c) OR bring up localization + full navigation stack + RViz
ros2 launch testbed_navigation navigation.launch.py
```

In RViz:
1. Use **2D Pose Estimate** to seed AMCL near the robot's actual spawn pose
   (`x=0.0, y=5.0, yaw=0.0` — matches `testbed_gazebo/spawn_testbed.launch.py`
   and is already the `amcl_params.yaml` default via `set_initial_pose`).
2. Drive the robot a little (e.g. `ros2 run teleop_twist_keyboard
   teleop_twist_keyboard`) so the particle cloud converges around the true
   pose.
3. Use **Nav2 Goal** to send a `NavigateToPose` goal and watch the global
   plan (green) and the robot follow it.

## Launch arguments

| Argument | Default | Used in |
|---|---|---|
| `map` | `testbed_bringup/maps/testbed_world.yaml` | map_loader, localization |
| `params_file` | `config/amcl_params.yaml` / `config/nav2_params.yaml` | localization, navigation |
| `use_sim_time` | `true` | all |
| `autostart` | `true` | all |
| `use_rviz` | `true` | navigation |

## Challenges / notes

- The starter code shipped with several intentional bugs that blocked every
  step of this workflow (wrong map image filename, an uninstalled `maps/`
  directory, a CMake syntax error that failed the whole
  `testbed_description` build, malformed sensor-plugin XML, and a 1.5 m
  lidar range far too short for the ~20×20 m map). These are documented and
  fixed — see `BUGS_AND_FIXES.md` in the repository root.
- AMCL's declarative `set_initial_pose` auto-seeding turned out to be
  unreliable on this Nav2/Humble build (AMCL would sit indefinitely logging
  "cannot publish a pose... please set the initial pose"). `localization.launch.py`
  now explicitly publishes a single `/initialpose` message ~6 seconds after
  bringup (matching the robot's real Gazebo spawn pose) instead of relying
  on that mechanism, which fixed it.
- **Wobbling/oscillating right after reaching a goal**: when a goal is close
  to a tight corner, the robot can reach the xy tolerance but then be unable
  to find a collision-free in-place rotation to finish aligning to the goal
  yaw, since there's too little clearance around it once the costmap's
  inflation is applied. `controller_server` retries every cycle, fails
  ("No valid trajectories", "Hits Unreachable Area"), and this retry loop
  looks like wobbling. It was made much less likely by: growing
  `local_costmap`'s rolling window from 4×4 m to 6×6 m (so the tail of the
  global plan stays inside the local window through sharp turns near
  corners), tightening the inflation radius from 0.4 m to 0.3 m with a
  steeper `cost_scaling_factor` (5.0) so more of the actually-navigable
  space near walls is usable, and loosening `yaw_goal_tolerance` from 0.2 to
  0.35 rad so the controller isn't chasing a razor-precise final heading in
  a tight spot. Goals placed in open areas were unaffected even before this
  tuning; this only shows up for goals very close to walls/corners.
- `nav2_params.yaml` intentionally keeps `local_costmap`'s `robot_base_frame`
  as `base_footprint` (matching `robot_base_frame` in the diff_drive plugin
  in `testbed.gazebo`) rather than `base_link`, since that's the frame the
  Gazebo plugin actually publishes odometry/TF for.
