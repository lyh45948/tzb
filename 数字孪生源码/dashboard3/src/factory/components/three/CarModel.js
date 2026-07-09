import * as THREE from 'three'

// Shared geometries — created once, reused by all AGV instances
const sharedGeo = {
  chassis: new THREE.BoxGeometry(1.1, 0.08, 0.7),
  body: new THREE.BoxGeometry(0.9, 0.2, 0.55),
  wheel: new THREE.CylinderGeometry(0.1, 0.1, 0.08, 16),
  tread: new THREE.TorusGeometry(0.09, 0.015, 4, 16),
  arch: new THREE.BoxGeometry(0.16, 0.06, 0.18),
  towerBase: new THREE.CylinderGeometry(0.06, 0.08, 0.12, 8),
  towerDome: new THREE.SphereGeometry(0.06, 8, 6, 0, Math.PI * 2, 0, Math.PI / 2),
  topPanel: new THREE.BoxGeometry(0.35, 0.015, 0.25),
  panelFrame: new THREE.BoxGeometry(0.38, 0.02, 0.28),
  bumper: new THREE.BoxGeometry(0.12, 0.04, 0.5),
  sensorStrip: new THREE.BoxGeometry(0.01, 0.015, 0.4),
  ledBody: new THREE.CylinderGeometry(0.012, 0.012, 0.025, 8),
  ledGlow: new THREE.SphereGeometry(0.018, 8, 8),
  cameraArm: new THREE.CylinderGeometry(0.015, 0.015, 0.1, 6),
  cameraHead: new THREE.BoxGeometry(0.04, 0.03, 0.05),
  sensorBody: new THREE.CylinderGeometry(0.08, 0.08, 0.25, 10),
  sensorCap: new THREE.CylinderGeometry(0.04, 0.04, 0.02, 8),
  warningArm: new THREE.CylinderGeometry(0.01, 0.01, 0.2, 6),
  warningNozzle: new THREE.ConeGeometry(0.02, 0.03, 6),
  scannerBody: new THREE.BoxGeometry(0.22, 0.16, 0.18),
  cargoTray: new THREE.BoxGeometry(0.42, 0.04, 0.34),
  cargoBox: new THREE.BoxGeometry(0.32, 0.18, 0.24)
}

/**
 * Procedural 3D factory AGV model with task-specific modules
 */
export class CarModel {
  constructor(scene, color = 0x1a73e8, type = 'patrol') {
    this.scene = scene
    this.group = new THREE.Group()
    this.wheels = []
    this.led = null
    this.type = type

    // Warning particle system for gas-monitoring AGVs
    this.warningParticles = null
    this.warningPositions = null
    this.warningVelocities = null
    this.warningLifetimes = null

    this._build(color, type)
    this.scene.add(this.group)
  }

  _build(color, type) {
    const chassisMat = new THREE.MeshStandardMaterial({ color: 0x1a1a1a, metalness: 0.3, roughness: 0.7 })
    const chassis = new THREE.Mesh(sharedGeo.chassis, chassisMat)
    chassis.position.y = 0.08
    chassis.castShadow = true
    this.group.add(chassis)

    const bodyMat = new THREE.MeshStandardMaterial({ color, metalness: 0.6, roughness: 0.35 })
    const body = new THREE.Mesh(sharedGeo.body, bodyMat)
    body.position.y = 0.22
    body.castShadow = true
    this.group.add(body)

    const archMat = new THREE.MeshStandardMaterial({ color: 0x2a2a2a, metalness: 0.4, roughness: 0.6 })
    const archPositions = [
      [0.38, 0.14, 0.32], [0.38, 0.14, -0.32],
      [-0.38, 0.14, 0.32], [-0.38, 0.14, -0.32]
    ]
    archPositions.forEach(pos => {
      const arch = new THREE.Mesh(sharedGeo.arch, archMat)
      arch.position.set(...pos)
      arch.castShadow = true
      this.group.add(arch)
    })

    const wheelMat = new THREE.MeshStandardMaterial({ color: 0x222222, metalness: 0.1, roughness: 0.9 })
    const treadMat = new THREE.MeshStandardMaterial({ color: 0x333333, metalness: 0.2, roughness: 0.8 })
    const wheelPositions = [
      [0.38, 0.1, 0.4], [0.38, 0.1, -0.4],
      [-0.38, 0.1, 0.4], [-0.38, 0.1, -0.4]
    ]
    wheelPositions.forEach(pos => {
      const wheel = new THREE.Mesh(sharedGeo.wheel, wheelMat)
      wheel.rotation.x = Math.PI / 2
      wheel.position.set(...pos)
      wheel.castShadow = true
      this.wheels.push(wheel)
      this.group.add(wheel)

      const tread = new THREE.Mesh(sharedGeo.tread, treadMat)
      tread.rotation.y = Math.PI / 2
      tread.position.set(pos[0], pos[1], pos[2])
      this.group.add(tread)
    })

    const towerMat = new THREE.MeshStandardMaterial({ color: 0x444444, metalness: 0.5, roughness: 0.4 })
    const towerBase = new THREE.Mesh(sharedGeo.towerBase, towerMat)
    towerBase.position.set(0, 0.38, 0)
    towerBase.castShadow = true
    this.group.add(towerBase)

    const towerDome = new THREE.Mesh(sharedGeo.towerDome, towerMat)
    towerDome.position.set(0, 0.44, 0)
    this.group.add(towerDome)

    const frameMat = new THREE.MeshStandardMaterial({ color: 0x888888, metalness: 0.7, roughness: 0.3 })
    const frame = new THREE.Mesh(sharedGeo.panelFrame, frameMat)
    frame.position.set(-0.15, 0.36, 0)
    frame.rotation.z = -0.15
    frame.castShadow = true
    this.group.add(frame)

    const panelMat = new THREE.MeshStandardMaterial({ color: 0x1a3a6a, metalness: 0.8, roughness: 0.15 })
    const panel = new THREE.Mesh(sharedGeo.topPanel, panelMat)
    panel.position.set(-0.15, 0.37, 0)
    panel.rotation.z = -0.15
    this.group.add(panel)

    const bumperMat = new THREE.MeshStandardMaterial({ color: 0x333333, metalness: 0.3, roughness: 0.6 })
    const bumper = new THREE.Mesh(sharedGeo.bumper, bumperMat)
    bumper.position.set(0.55, 0.1, 0)
    bumper.castShadow = true
    this.group.add(bumper)

    const sensorMat = new THREE.MeshStandardMaterial({
      color: 0x00e676, emissive: 0x00e676, emissiveIntensity: 0.5
    })
    const sensorStrip = new THREE.Mesh(sharedGeo.sensorStrip, sensorMat)
    sensorStrip.position.set(0.56, 0.1, 0)
    this.group.add(sensorStrip)

    this._addTaskAttachment(type, color)

    const ledBodyMat = new THREE.MeshStandardMaterial({ color: 0x888888, metalness: 0.5 })
    const ledGlowMat = new THREE.MeshStandardMaterial({
      color: 0x00d4ff, emissive: 0x00d4ff, emissiveIntensity: 0.5,
      transparent: true, opacity: 0.85
    })

    const ledPositions = [[0.52, 0.2, 0.18], [0.52, 0.2, -0.18]]
    ledPositions.forEach(pos => {
      const ledBody = new THREE.Mesh(sharedGeo.ledBody, ledBodyMat)
      ledBody.position.set(...pos)
      this.group.add(ledBody)
      const ledGlow = new THREE.Mesh(sharedGeo.ledGlow, ledGlowMat.clone())
      ledGlow.position.set(pos[0], pos[1] + 0.02, pos[2])
      this.group.add(ledGlow)
    })

    const beaconMat = new THREE.MeshStandardMaterial({
      color: 0x00d4ff, emissive: 0x00d4ff, emissiveIntensity: 0.5,
      transparent: true, opacity: 0.9
    })
    this.led = new THREE.Mesh(sharedGeo.ledGlow, beaconMat)
    this.led.position.set(0, 0.52, 0)
    this.group.add(this.led)
  }

  _addTaskAttachment(type, color) {
    if (type === 'patrol') {
      this._addPatrolAttachment()
    } else if (type === 'gasMonitor') {
      this._addGasMonitorAttachment()
    } else if (type === 'goodsCount') {
      this._addGoodsScannerAttachment(color)
    } else if (type === 'obstacleAvoidance') {
      this._addObstacleSensorAttachment()
    } else if (type === 'materialTransfer') {
      this._addCargoAttachment(color)
    }
  }

  _addPatrolAttachment() {
    const armMat = new THREE.MeshStandardMaterial({ color: 0x555555, metalness: 0.5, roughness: 0.4 })
    const headMat = new THREE.MeshStandardMaterial({ color: 0x222222, metalness: 0.6, roughness: 0.3 })

    const arm = new THREE.Mesh(sharedGeo.cameraArm, armMat)
    arm.position.set(0.2, 0.42, 0)
    this.group.add(arm)

    const cam = new THREE.Mesh(sharedGeo.cameraHead, headMat)
    cam.position.set(0.2, 0.5, 0)
    cam.castShadow = true
    this.group.add(cam)

    const lensMat = new THREE.MeshStandardMaterial({ color: 0x111111, metalness: 0.9, roughness: 0.1 })
    const lens = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.01, 8), lensMat)
    lens.rotation.z = Math.PI / 2
    lens.position.set(0.225, 0.5, 0)
    this.group.add(lens)
  }

  _addGasMonitorAttachment() {
    const sensorMat = new THREE.MeshStandardMaterial({ color: 0x7f1d1d, metalness: 0.4, roughness: 0.3 })
    const capMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, emissive: 0x7c2d12, emissiveIntensity: 0.35 })

    const body = new THREE.Mesh(sharedGeo.sensorBody, sensorMat)
    body.position.set(-0.3, 0.42, 0)
    body.castShadow = true
    this.group.add(body)

    const cap = new THREE.Mesh(sharedGeo.sensorCap, capMat)
    cap.position.set(-0.3, 0.56, 0)
    this.group.add(cap)

    const armMat = new THREE.MeshStandardMaterial({ color: 0x666666, metalness: 0.5 })
    const warningArm = new THREE.Mesh(sharedGeo.warningArm, armMat)
    warningArm.rotation.z = Math.PI / 2
    warningArm.position.set(-0.15, 0.3, 0.35)
    this.group.add(warningArm)

    const nozzleMat = new THREE.MeshStandardMaterial({ color: 0x888888, metalness: 0.6 })
    const nozzle = new THREE.Mesh(sharedGeo.warningNozzle, nozzleMat)
    nozzle.position.set(-0.15, 0.3, 0.46)
    nozzle.rotation.x = Math.PI / 2
    this.group.add(nozzle)

    this._createWarningParticles()
  }

  _addGoodsScannerAttachment(color) {
    this._addCargoAttachment(color)
    const scannerMat = new THREE.MeshStandardMaterial({ color: 0x111827, metalness: 0.55, roughness: 0.28 })
    const lensMat = new THREE.MeshStandardMaterial({ color: 0x22c55e, emissive: 0x166534, emissiveIntensity: 0.45 })
    const scanner = new THREE.Mesh(sharedGeo.scannerBody, scannerMat)
    scanner.position.set(0.08, 0.48, 0)
    scanner.castShadow = true
    this.group.add(scanner)

    const lens = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.08, 0.11), lensMat)
    lens.position.set(0.2, 0.48, 0)
    this.group.add(lens)
  }

  _addObstacleSensorAttachment() {
    const sensorMat = new THREE.MeshStandardMaterial({ color: 0x06b6d4, emissive: 0x0e7490, emissiveIntensity: 0.35 })
    for (let z = -0.22; z <= 0.22; z += 0.22) {
      const sensor = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.035, 12), sensorMat)
      sensor.rotation.z = Math.PI / 2
      sensor.position.set(0.63, 0.19, z)
      this.group.add(sensor)
    }
  }

  _addCargoAttachment(color) {
    const trayMat = new THREE.MeshStandardMaterial({ color: 0x374151, metalness: 0.45, roughness: 0.4 })
    const boxMat = new THREE.MeshStandardMaterial({ color, roughness: 0.65 })
    const tray = new THREE.Mesh(sharedGeo.cargoTray, trayMat)
    tray.position.set(-0.25, 0.38, 0)
    tray.castShadow = true
    this.group.add(tray)

    const box = new THREE.Mesh(sharedGeo.cargoBox, boxMat)
    box.position.set(-0.25, 0.5, 0)
    box.castShadow = true
    this.group.add(box)
  }

  _createWarningParticles() {
    const particleCount = 36
    const positions = new Float32Array(particleCount * 3)
    for (let i = 0; i < particleCount; i++) {
      positions[i * 3 + 1] = -100
    }
    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    const material = new THREE.PointsMaterial({
      color: 0xf97316,
      size: 0.065,
      transparent: true,
      opacity: 0.65,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    })

    this.warningParticles = new THREE.Points(geometry, material)
    this.warningParticles.position.set(-0.15, 0.28, 0.46)
    this.warningParticles.visible = false
    this.group.add(this.warningParticles)

    this.warningPositions = positions
    this.warningVelocities = new Float32Array(particleCount * 3)
    this.warningLifetimes = new Float32Array(particleCount)
    for (let i = 0; i < particleCount; i++) {
      this.warningLifetimes[i] = 0
    }
  }

  updateWarning(isActive, deltaTime) {
    if (!this.warningParticles) return
    this.warningParticles.visible = isActive
    if (!isActive) return

    const posAttr = this.warningParticles.geometry.attributes.position
    const count = this.warningLifetimes.length

    for (let i = 0; i < count; i++) {
      this.warningLifetimes[i] -= deltaTime
      if (this.warningLifetimes[i] <= 0) {
        this.warningPositions[i * 3] = 0
        this.warningPositions[i * 3 + 1] = 0
        this.warningPositions[i * 3 + 2] = 0
        const angle = (Math.random() - 0.5) * 1.1
        const speed = 0.25 + Math.random() * 0.35
        this.warningVelocities[i * 3] = Math.sin(angle) * speed * 0.25
        this.warningVelocities[i * 3 + 1] = speed * (0.6 + Math.random() * 0.5)
        this.warningVelocities[i * 3 + 2] = Math.cos(angle) * speed * 0.45
        this.warningLifetimes[i] = 0.35 + Math.random() * 0.45
      }
      this.warningPositions[i * 3] += this.warningVelocities[i * 3] * deltaTime
      this.warningPositions[i * 3 + 1] += this.warningVelocities[i * 3 + 1] * deltaTime
      this.warningPositions[i * 3 + 2] += this.warningVelocities[i * 3 + 2] * deltaTime
      this.warningVelocities[i * 3 + 1] -= 0.55 * deltaTime
    }

    posAttr.array = this.warningPositions
    posAttr.needsUpdate = true
  }

  updateWheelRotation(speed) {
    const rot = Math.abs(speed || 0) * 0.002
    this.wheels.forEach(w => { w.rotation.z += rot })
  }

  updateLED(brightness) {
    if (this.led) {
      this.led.material.emissiveIntensity = (brightness || 0) / 100
    }
  }

  setPosition(x, z) {
    this.group.position.x = x
    this.group.position.z = z
  }

  setRotation(y) {
    this.group.rotation.y = y
  }

  dispose() {
    // 递归清理 group 内所有 mesh 的独立材质（共享材质不 dispose，避免影响其他实例）
    this.group.traverse((child) => {
      if (child.geometry && !Object.values(sharedGeo).includes(child.geometry)) {
        child.geometry.dispose()
      }
      if (child.material) {
        // 共享材质（在 sharedGeo 之外由 _build 创建的材质实例）需要释放
        // 判断：非共享材质 = 该材质不被其他 CarModel 引用
        if (Array.isArray(child.material)) {
          child.material.forEach(m => m.dispose())
        } else {
          child.material.dispose()
        }
      }
    })
    // 清理 warning particles 的独立 geometry/material
    if (this.warningParticles) {
      if (this.warningParticles.geometry) this.warningParticles.geometry.dispose()
      if (this.warningParticles.material) this.warningParticles.material.dispose()
      this.warningParticles = null
    }
    this.scene.remove(this.group)
  }
}
