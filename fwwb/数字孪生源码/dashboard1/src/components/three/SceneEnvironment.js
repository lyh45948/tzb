import * as THREE from 'three'
import { FACTORY_WAYPOINTS } from '../../utils/waypoints'

export class SceneEnvironment {
  constructor(scene) {
    this.scene = scene
    this.ambientLight = null
    this.directionalLight = null
    this.ceilingLights = []
    this.waypointMarkers = [] // { id, x, z, group, color }
    this._setup()
  }

  _setup() {
    this._createFactoryFloor()
    this._createAgvLanes()
    this._createProductionLines()
    this._createStorageShelves()
    this._createSafetyZones()
    this._createChargingStation()
    this._createGoodsArea()
    this._createBoundaryWalls()
    this._createLightingRig()
    this._createWaypointMarkers()

    this.ambientLight = new THREE.AmbientLight(0xffffff, 0.55)
    this.scene.add(this.ambientLight)

    this.directionalLight = new THREE.DirectionalLight(0xffffff, 0.75)
    this.directionalLight.position.set(8, 16, 10)
    this.directionalLight.castShadow = true
    this.directionalLight.shadow.mapSize.set(2048, 2048)
    this.directionalLight.shadow.camera.near = 0.5
    this.directionalLight.shadow.camera.far = 50
    this.directionalLight.shadow.camera.left = -16
    this.directionalLight.shadow.camera.right = 16
    this.directionalLight.shadow.camera.top = 16
    this.directionalLight.shadow.camera.bottom = -16
    this.scene.add(this.directionalLight)

    const hemi = new THREE.HemisphereLight(0xdbeafe, 0x475569, 0.25)
    this.scene.add(hemi)

    this.scene.background = new THREE.Color(0xe2e8f0)
    this.scene.fog = new THREE.Fog(0xe2e8f0, 38, 62)
  }

  _createFactoryFloor() {
    const base = new THREE.Mesh(
      new THREE.PlaneGeometry(34, 24),
      new THREE.MeshStandardMaterial({ color: 0xb8c2cc, roughness: 0.88, metalness: 0.04 })
    )
    base.rotation.x = -Math.PI / 2
    base.position.y = -0.02
    base.receiveShadow = true
    this.scene.add(base)

    const epoxy = new THREE.Mesh(
      new THREE.PlaneGeometry(30, 20),
      new THREE.MeshStandardMaterial({ color: 0xd9e2ec, roughness: 0.62, metalness: 0.08 })
    )
    epoxy.rotation.x = -Math.PI / 2
    epoxy.position.y = -0.01
    epoxy.receiveShadow = true
    this.scene.add(epoxy)

    const grid = new THREE.GridHelper(30, 30, 0x64748b, 0x94a3b8)
    grid.position.y = 0.012
    grid.material.opacity = 0.16
    grid.material.transparent = true
    this.scene.add(grid)
  }

  _createAgvLanes() {
    const laneMat = new THREE.MeshStandardMaterial({ color: 0x2563eb, roughness: 0.5 })
    const warnMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.55 })

    const lanes = [
      { x: 0, z: -7, w: 24, h: 0.16 },
      { x: 0, z: 7, w: 24, h: 0.16 },
      { x: -11, z: 0, w: 0.16, h: 14 },
      { x: 11, z: 0, w: 0.16, h: 14 },
      { x: 0, z: -2, w: 22, h: 0.12 },
      { x: 0, z: 3, w: 22, h: 0.12 }
    ]

    lanes.forEach(lane => {
      const mesh = new THREE.Mesh(new THREE.PlaneGeometry(lane.w, lane.h), laneMat)
      mesh.rotation.x = -Math.PI / 2
      mesh.position.set(lane.x, 0.006, lane.z)
      this.scene.add(mesh)
    })

    for (let x = -12; x <= 12; x += 2) {
      const mark = new THREE.Mesh(new THREE.PlaneGeometry(0.7, 0.08), warnMat)
      mark.rotation.x = -Math.PI / 2
      mark.rotation.z = -0.65
      mark.position.set(x, 0.01, -8.6)
      this.scene.add(mark)
    }
  }

  _createProductionLines() {
    const machineMat = new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.35, roughness: 0.42 })
    const screenMat = new THREE.MeshStandardMaterial({ color: 0x22c55e, emissive: 0x14532d, emissiveIntensity: 0.35 })
    const beltMat = new THREE.MeshStandardMaterial({ color: 0x1f2937, roughness: 0.7 })
    const railMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.6, roughness: 0.28 })

    const stations = [
      { x: -3.5, z: -4.8, name: 'CNC-01' },
      { x: 1.2, z: -4.8, name: '装配-01' },
      { x: 6, z: -4.8, name: '质检-01' },
      { x: -3.5, z: 1.2, name: '焊接-01' },
      { x: 1.2, z: 1.2, name: '包装-01' },
      { x: 6, z: 1.2, name: '计数-01' }
    ]

    stations.forEach(({ x, z }) => {
      const base = new THREE.Mesh(new THREE.BoxGeometry(1.35, 0.9, 1.05), machineMat)
      base.position.set(x, 0.45, z)
      base.castShadow = true
      base.receiveShadow = true
      this.scene.add(base)

      const screen = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.28, 0.03), screenMat)
      screen.position.set(x, 0.72, z + 0.54)
      this.scene.add(screen)

      const tower = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.7, 8), railMat)
      tower.position.set(x + 0.55, 1.25, z - 0.35)
      tower.castShadow = true
      this.scene.add(tower)
    })

    const conveyors = [
      { x: 1.2, z: -3.2, w: 10.8, h: 0.58 },
      { x: 1.2, z: 2.8, w: 10.8, h: 0.58 }
    ]
    conveyors.forEach(c => {
      const belt = new THREE.Mesh(new THREE.BoxGeometry(c.w, 0.12, c.h), beltMat)
      belt.position.set(c.x, 0.12, c.z)
      belt.castShadow = true
      belt.receiveShadow = true
      this.scene.add(belt)

      const rail1 = new THREE.Mesh(new THREE.BoxGeometry(c.w, 0.08, 0.06), railMat)
      rail1.position.set(c.x, 0.25, c.z - c.h / 2)
      this.scene.add(rail1)
      const rail2 = rail1.clone()
      rail2.position.z = c.z + c.h / 2
      this.scene.add(rail2)
    })
  }

  _createStorageShelves() {
    const frameMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.6, roughness: 0.35 })
    const boxMats = [0xf97316, 0x2563eb, 0x22c55e, 0xf59e0b].map(color => new THREE.MeshStandardMaterial({ color, roughness: 0.72 }))

    for (let row = 0; row < 3; row++) {
      const z = -5.8 + row * 3.4
      const shelf = new THREE.Mesh(new THREE.BoxGeometry(0.18, 1.45, 2.4), frameMat)
      shelf.position.set(-13.2, 0.72, z)
      shelf.castShadow = true
      this.scene.add(shelf)

      for (let level = 0; level < 3; level++) {
        const beam = new THREE.Mesh(new THREE.BoxGeometry(2.1, 0.08, 0.12), frameMat)
        beam.position.set(-12.2, 0.32 + level * 0.45, z - 1.05)
        this.scene.add(beam)
        const beam2 = beam.clone()
        beam2.position.z = z + 1.05
        this.scene.add(beam2)
      }

      for (let i = 0; i < 6; i++) {
        const box = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.32, 0.46), boxMats[(i + row) % boxMats.length])
        box.position.set(-12.2, 0.2 + (i % 3) * 0.44, z - 0.65 + Math.floor(i / 3) * 1.3)
        box.castShadow = true
        this.scene.add(box)
      }
    }
  }

  _createSafetyZones() {
    const gasMat = new THREE.MeshStandardMaterial({ color: 0xef4444, transparent: true, opacity: 0.18, roughness: 0.4 })
    const borderMat = new THREE.MeshStandardMaterial({ color: 0xef4444, roughness: 0.5 })
    const zone = new THREE.Mesh(new THREE.PlaneGeometry(4.4, 3.4), gasMat)
    zone.rotation.x = -Math.PI / 2
    zone.position.set(8.8, 0.015, 5.9)
    this.scene.add(zone)

    const edges = [
      { x: 8.8, z: 4.2, w: 4.4, h: 0.08 },
      { x: 8.8, z: 7.6, w: 4.4, h: 0.08 },
      { x: 6.6, z: 5.9, w: 0.08, h: 3.4 },
      { x: 11, z: 5.9, w: 0.08, h: 3.4 }
    ]
    edges.forEach(e => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(e.w, e.h), borderMat)
      m.rotation.x = -Math.PI / 2
      m.position.set(e.x, 0.025, e.z)
      this.scene.add(m)
    })

    const sensor = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 1.2, 16), new THREE.MeshStandardMaterial({ color: 0x7f1d1d, metalness: 0.35, roughness: 0.4 }))
    sensor.position.set(10.6, 0.6, 7.1)
    sensor.castShadow = true
    this.scene.add(sensor)
  }

  _createChargingStation() {
    const dockMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.45, roughness: 0.35 })
    const glowMat = new THREE.MeshStandardMaterial({ color: 0x06b6d4, emissive: 0x0891b2, emissiveIntensity: 0.5 })
    const dock = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.22, 1.15), dockMat)
    dock.position.set(-7.5, 0.12, 8.5)
    dock.castShadow = true
    this.scene.add(dock)

    const panel = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.7, 0.8), glowMat)
    panel.position.set(-8.7, 0.55, 8.5)
    this.scene.add(panel)
  }

  _createGoodsArea() {
    const palletMat = new THREE.MeshStandardMaterial({ color: 0x8b5a2b, roughness: 0.8 })
    const boxMat = new THREE.MeshStandardMaterial({ color: 0xd97706, roughness: 0.72 })

    for (let i = 0; i < 7; i++) {
      const x = -2 + (i % 4) * 1.1
      const z = 7.2 + Math.floor(i / 4) * 0.9
      const pallet = new THREE.Mesh(new THREE.BoxGeometry(0.85, 0.08, 0.62), palletMat)
      pallet.position.set(x, 0.04, z)
      this.scene.add(pallet)

      const box = new THREE.Mesh(new THREE.BoxGeometry(0.65, 0.38, 0.48), boxMat)
      box.position.set(x, 0.28, z)
      box.castShadow = true
      this.scene.add(box)
    }
  }

  _createBoundaryWalls() {
    const wallMat = new THREE.MeshStandardMaterial({ color: 0xcbd5e1, roughness: 0.68 })
    const railMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.45, roughness: 0.35 })
    const walls = [
      { x: 0, z: -10.3, w: 31, h: 0.18 },
      { x: 0, z: 10.3, w: 31, h: 0.18 },
      { x: -15.5, z: 0, w: 0.18, h: 20.6 },
      { x: 15.5, z: 0, w: 0.18, h: 20.6 }
    ]
    walls.forEach(w => {
      const wall = new THREE.Mesh(new THREE.BoxGeometry(w.w, 1.2, w.h), wallMat)
      wall.position.set(w.x, 0.6, w.z)
      wall.castShadow = true
      wall.receiveShadow = true
      this.scene.add(wall)
    })

    for (let x = -12; x <= 12; x += 4) {
      const rail = new THREE.Mesh(new THREE.BoxGeometry(0.08, 1.8, 0.08), railMat)
      rail.position.set(x, 0.9, -9.7)
      rail.castShadow = true
      this.scene.add(rail)
    }
  }

  _createLightingRig() {
    const barMat = new THREE.MeshStandardMaterial({ color: 0x64748b, metalness: 0.5, roughness: 0.25 })
    const lampMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xdbeafe, emissiveIntensity: 0.45 })

    for (let z = -6; z <= 6; z += 6) {
      const bar = new THREE.Mesh(new THREE.BoxGeometry(24, 0.06, 0.06), barMat)
      bar.position.set(0, 4.2, z)
      this.scene.add(bar)

      for (let x = -10; x <= 10; x += 5) {
        const lamp = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.06, 0.28), lampMat)
        lamp.position.set(x, 4.05, z)
        this.scene.add(lamp)
        const light = new THREE.PointLight(0xdbeafe, 0.35, 8)
        light.position.set(x, 3.8, z)
        this.ceilingLights.push(light)
        this.scene.add(light)
      }
    }
  }

  _createWaypointMarkers() {
    // 每个调度点位:地面圆环 + 中心圆盘 + 立柱(顶端球),便于在 3D 视角识别
    const ringGeo = new THREE.RingGeometry(0.6, 0.78, 32)
    const diskGeo = new THREE.CircleGeometry(0.55, 32)
    const poleGeo = new THREE.CylinderGeometry(0.05, 0.05, 0.9, 12)
    const beaconGeo = new THREE.SphereGeometry(0.13, 14, 12)

    FACTORY_WAYPOINTS.forEach(wp => {
      const colorHex = parseInt(wp.color.replace('#', ''), 16)
      const colorObj = new THREE.Color(colorHex)
      const group = new THREE.Group()
      group.position.set(wp.x, 0, wp.z)

      const ring = new THREE.Mesh(
        ringGeo,
        new THREE.MeshBasicMaterial({ color: colorObj, transparent: true, opacity: 0.9, side: THREE.DoubleSide })
      )
      ring.rotation.x = -Math.PI / 2
      ring.position.y = 0.018
      group.add(ring)

      const disk = new THREE.Mesh(
        diskGeo,
        new THREE.MeshBasicMaterial({ color: colorObj, transparent: true, opacity: 0.22, side: THREE.DoubleSide })
      )
      disk.rotation.x = -Math.PI / 2
      disk.position.y = 0.014
      group.add(disk)

      const pole = new THREE.Mesh(
        poleGeo,
        new THREE.MeshStandardMaterial({ color: 0xf8fafc, metalness: 0.3, roughness: 0.4 })
      )
      pole.position.y = 0.45
      group.add(pole)

      const beacon = new THREE.Mesh(
        beaconGeo,
        new THREE.MeshStandardMaterial({ color: colorObj, emissive: colorObj, emissiveIntensity: 0.7 })
      )
      beacon.position.y = 0.95
      group.add(beacon)

      group.userData.waypointId = wp.id
      this.scene.add(group)
      this.waypointMarkers.push({ id: wp.id, name: wp.name, x: wp.x, z: wp.z, color: wp.color, group, beacon })
    })
  }

  // 让 beacon 缓慢呼吸,提示这是交互点
  pulseWaypointBeacons(time) {
    if (!this.waypointMarkers) return
    const t = (time || 0) * 0.001
    this.waypointMarkers.forEach((m, i) => {
      m.beacon.material.emissiveIntensity = 0.55 + Math.sin(t * 1.6 + i * 0.4) * 0.4
    })
  }

  updateLux(lux) {
    const normalized = Math.min(1.2, Math.max(0.35, lux / 1000))
    if (this.ambientLight) this.ambientLight.intensity = 0.35 + normalized * 0.25
    if (this.directionalLight) this.directionalLight.intensity = 0.45 + normalized * 0.35
    this.ceilingLights.forEach(light => {
      light.intensity = 0.2 + normalized * 0.28
    })
  }
}
