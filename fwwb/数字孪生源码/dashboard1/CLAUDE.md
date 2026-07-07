# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This directory is a standalone Vue/Vite smart factory digital-twin dashboard. It renders a full-screen safety monitoring board with simulated AGV telemetry, workshop environment/gas-safety data, ECharts panels, and a Three.js factory scene. The app is currently demo-only: `src/config.js` sets `demoMode: true`, and runtime data is generated locally rather than fetched from the `fwwb/backend` services.

## Commands

Use npm; this project has a `package-lock.json`.

```bash
npm install          # install dependencies
npm run dev          # start Vite dev server on 0.0.0.0:5173
npm run build        # production build into dist/
npm run preview      # serve the built dist/ output
```

There are no lint, type-check, or test scripts in `package.json`. Before handing off dashboard changes, run `npm run build`; it currently succeeds but emits Vite's large-chunk warning because Three.js/ECharts are bundled into the main chunk.

## Architecture

- `src/main.js` creates the Vue 3 app, installs Pinia, and mounts `App.vue`.
- `src/App.vue` only renders `DashboardLayout`, so page composition lives in `src/components/layout/DashboardLayout.vue`.
- `DashboardLayout.vue` owns the full-screen shell: top header, left `SidebarNav`, left/right side panels, central Three.js scene, and footer panels. It starts/stops the simulation by calling the Pinia device store on mount/unmount.
- `src/stores/deviceStore.js` is the central state and simulation loop. It stores workshop environment readings, gas/flame safety status, AGV fleet state, selected robot, manual-control overrides, alarm events, and chart history arrays. `startSimulation()` runs every `config.chartUpdateInterval` milliseconds and uses `generateSimData()` / `generateFleetData()` from `src/utils/dataFormatter.js`.
- `src/config.js` contains app-wide demo parameters: update interval, history length intent, AGV count/names/colors, and factory floor size. Change these first when adjusting demo scale or timing.
- `src/utils/constants.js` contains shared label/color maps, alert levels, task/status names, and sensor ranges. Use these maps instead of duplicating AGV status/task labels in components.

## UI and Data Flow

The app is component-driven and reads directly from the Pinia setup store:

1. `DashboardLayout` starts the simulation.
2. `deviceStore` updates refs for environment data, gas safety data, fleet data, manual state, alarm events, and history arrays.
3. Chart and panel components read the store and update their ECharts/options or templates.
4. `CarScene.vue` reads `store.fleet` every animation frame through `AnimationController` to move 3D AGV models and update floating labels.
5. `ControlPanel.vue` updates `selectedRobotId`, toggles manual overrides, and sends movement directions back into the store; the next simulation ticks use those overrides to generate fleet positions.
6. `SidebarNav.vue` is local visual navigation only; it does not use Vue Router and does not call backend APIs.

Because Pinia setup stores unwrap refs on the store instance, existing components use `store.selectedRobotId = ...` and `store.fleet` directly rather than `.value`.

## Three.js Scene Structure

The central 3D view is split across small classes:

- `src/components/three/CarScene.vue` initializes WebGL renderer, CSS2D label renderer, camera, OrbitControls, raycaster selection, resize handling, and the animation loop.
- `src/components/three/CarModel.js` builds procedural AGV meshes with shared geometries and task-specific modules (`patrol`, `gasMonitor`, `goodsCount`, `obstacleAvoidance`, `materialTransfer`). Dispose model resources when adding new geometries/materials.
- `src/components/three/AnimationController.js` interpolates model position/rotation from fleet data, animates wheels/LEDs/warning particles, and updates environment lighting from lux values.
- `src/components/three/SceneEnvironment.js` builds the factory floor, AGV lanes, production equipment, shelves, safety zones, charging station, goods area, and lighting rig.

`CarScene.vue` currently creates AGV types in a fixed order and assigns IDs as `robot_1`, `robot_2`, etc.; keep this aligned with `config.robotCount`, `config.robotNames`, and `generateFleetData()`.

## Styling Conventions

- Global CSS variables are in `src/assets/styles/variables.css`; shared base styles are in `src/assets/styles/global.css`.
- Most `.vue` files use `<script setup>` and scoped styles. `CarScene.vue` also has a non-scoped `<style>` block for CSS2DRenderer-created DOM labels.
- Existing comments and UI text are mixed English/Chinese. User-facing dashboard labels are primarily Chinese; preserve that style when adding panels or metrics.

## Current Integration Boundaries

The dashboard intentionally remains demo-only for now. It mirrors backend concepts such as temperature/humidity, lux, CO2/TVOC, gas/flame status, AGV mode/speed/distance, fan/LED/buzzer, and smart light state, but it does not fetch REST APIs or open WebSocket connections. If adding live backend integration later, introduce it explicitly and keep the demo simulation path available unless requirements say otherwise.
