/**
 * Animation controller for multiple factory AGVs
 */
export class AnimationController {
  constructor(carModels, sceneEnvironment) {
    this.models = carModels
    this.sceneEnv = sceneEnvironment
    this._lastTime = performance.now()
  }

  update(fleetData, lux) {
    if (!fleetData || !this.models.length) return

    const now = performance.now()
    const deltaTime = Math.min((now - this._lastTime) / 1000, 0.1) // cap at 100ms
    this._lastTime = now

    fleetData.forEach((robot, i) => {
      if (i >= this.models.length) return
      const model = this.models[i]

      const targetX = robot.position.x
      const targetZ = robot.position.z
      const curX = model.group.position.x
      const curZ = model.group.position.z

      model.group.position.x += (targetX - curX) * 0.08
      model.group.position.z += (targetZ - curZ) * 0.08

      const dx = targetX - curX
      const dz = targetZ - curZ
      if (Math.abs(dx) > 0.01 || Math.abs(dz) > 0.01) {
        const targetRot = Math.atan2(-dx, -dz)
        let curRot = model.group.rotation.y
        let diff = targetRot - curRot
        while (diff > Math.PI) diff -= Math.PI * 2
        while (diff < -Math.PI) diff += Math.PI * 2
        model.group.rotation.y += diff * 0.08
      }

      model.updateWheelRotation(robot.speed)
      model.updateLED(50 + Math.sin(Date.now() * 0.003 + i) * 30)

      if (model.type === 'gasMonitor') {
        model.updateWarning(robot.status === 'warning' || robot.alertLevel === 'critical', deltaTime)
      }
    })

    this.sceneEnv.updateLux(lux)
  }

  reset() {
    this.models.forEach((m) => {
      m.setPosition(0, 0)
      m.setRotation(0)
    })
  }
}
