/**
 * sensor-gauge.js
 * Circular progress gauge component for displaying sensor values
 *
 * Properties:
 * - value: Current sensor value (number)
 * - min: Minimum value (default: 0)
 * - max: Maximum value (default: 100)
 * - unit: Unit string to display
 * - label: Optional label below the gauge
 * - warningThreshold: Value threshold for warning status (optional)
 * - dangerThreshold: Value threshold for danger status (optional)
 * - size: Size variant - 'normal', 'warning', 'danger' (default: 'normal')
 * - decimalPlaces: Number of decimal places to display (default: 1)
 */

Component({
  properties: {
    // Current value
    value: {
      type: Number,
      value: 0,
      observer: 'onValueChange'
    },
    // Minimum value
    min: {
      type: Number,
      value: 0
    },
    // Maximum value
    max: {
      type: Number,
      value: 100
    },
    // Unit string
    unit: {
      type: String,
      value: ''
    },
    // Label text
    label: {
      type: String,
      value: ''
    },
    // Warning threshold
    warningThreshold: {
      type: Number,
      value: null
    },
    // Danger threshold
    dangerThreshold: {
      type: Number,
      value: null
    },
    // Size variant
    size: {
      type: String,
      value: 'normal'
    },
    // Decimal places
    decimalPlaces: {
      type: Number,
      value: 1
    }
  },

  data: {
    displayValue: '0',
    statusClass: 'status-normal',
    canvas: null,
    ctx: null,
    animatedValue: 0,
    animationFrame: null
  },

  lifetimes: {
    attached() {
      this.initCanvas();
    },

    detached() {
      if (this.data.animationFrame) {
        cancelAnimationFrame(this.data.animationFrame);
      }
    }
  },

  methods: {
    /**
     * Initialize canvas for drawing
     */
    initCanvas() {
      const query = this.createSelectorQuery();

      query.select('#gaugeCanvas')
        .fields({ node: true, size: true })
        .exec((res) => {
          if (!res || !res[0]) {
            console.warn('[sensor-gauge] Canvas not found');
            return;
          }

          const canvas = res[0].node;
          const ctx = canvas.getContext('2d');
          const dpr = wx.getSystemInfoSync().pixelRatio;

          canvas.width = res[0].width * dpr;
          canvas.height = res[0].height * dpr;
          ctx.scale(dpr, dpr);

          this.canvas = canvas;
          this.ctx = ctx;
          this.canvasWidth = res[0].width;
          this.canvasHeight = res[0].height;

          // Initial draw
          this.drawGauge(this.data.animatedValue);
        });
    },

    /**
     * Handle value change with animation
     */
    onValueChange(newVal, oldVal) {
      const displayValue = this.formatValue(newVal);
      const statusClass = this.getStatusClass(newVal);

      this.setData({
        displayValue,
        statusClass
      });

      // Animate value change
      this.animateValue(oldVal || 0, newVal);
    },

    /**
     * Format value for display
     */
    formatValue(value) {
      const decimals = this.properties.decimalPlaces;
      return value.toFixed(decimals);
    },

    /**
     * Get status class based on thresholds
     */
    getStatusClass(value) {
      const { warningThreshold, dangerThreshold } = this.properties;

      if (dangerThreshold !== null && value >= dangerThreshold) {
        return 'status-danger';
      }

      if (warningThreshold !== null && value >= warningThreshold) {
        return 'status-warning';
      }

      return 'status-normal';
    },

    /**
     * Get color based on status
     */
    getStatusColor(value) {
      const { warningThreshold, dangerThreshold } = this.properties;

      if (dangerThreshold !== null && value >= dangerThreshold) {
        return {
          primary: '#ee0a24',
          secondary: '#ffcccc',
          glow: 'rgba(238, 10, 36, 0.3)'
        };
      }

      if (warningThreshold !== null && value >= warningThreshold) {
        return {
          primary: '#ff9d00',
          secondary: '#fff3cd',
          glow: 'rgba(255, 157, 0, 0.3)'
        };
      }

      return {
        primary: '#07c160',
        secondary: '#e8f5e9',
        glow: 'rgba(7, 193, 96, 0.3)'
      };
    },

    /**
     * Animate value change
     */
    animateValue(from, to) {
      if (this.animationFrame) {
        cancelAnimationFrame(this.animationFrame);
      }

      const duration = 500; // Animation duration in ms
      const startTime = Date.now();
      const diff = to - from;

      const animate = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Ease out cubic
        const easeProgress = 1 - Math.pow(1 - progress, 3);

        const currentValue = from + diff * easeProgress;
        this.drawGauge(currentValue);

        if (progress < 1) {
          this.animationFrame = requestAnimationFrame(animate);
        }
      };

      animate();
    },

    /**
     * Draw the circular gauge
     */
    drawGauge(currentValue) {
      if (!this.ctx || !this.canvas) return;

      const ctx = this.ctx;
      const width = this.canvasWidth;
      const height = this.canvasHeight;
      const centerX = width / 2;
      const centerY = height / 2;

      // Calculate radius (leave space for stroke)
      const strokeWidth = Math.max(width, height) * 0.1;
      const radius = Math.min(width, height) / 2 - strokeWidth / 2 - 2;

      // Calculate percentage
      const { min, max } = this.properties;
      const range = max - min || 1;
      const percentage = Math.max(0, Math.min(1, (currentValue - min) / range));

      // Get colors based on current value
      const colors = this.getStatusColor(currentValue);

      // Clear canvas
      ctx.clearRect(0, 0, width, height);

      // Draw background circle
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
      ctx.strokeStyle = '#f0f0f0';
      ctx.lineWidth = strokeWidth;
      ctx.lineCap = 'round';
      ctx.stroke();

      // Draw progress arc
      if (percentage > 0) {
        const startAngle = -Math.PI / 2; // Start from top
        const endAngle = startAngle + (Math.PI * 2 * percentage);

        // Draw glow effect for warning/danger
        if (currentValue >= this.properties.warningThreshold) {
          ctx.beginPath();
          ctx.arc(centerX, centerY, radius, startAngle, endAngle);
          ctx.strokeStyle = colors.glow;
          ctx.lineWidth = strokeWidth + 4;
          ctx.lineCap = 'round';
          ctx.stroke();
        }

        // Draw main progress arc
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, startAngle, endAngle);
        ctx.strokeStyle = colors.primary;
        ctx.lineWidth = strokeWidth;
        ctx.lineCap = 'round';
        ctx.stroke();

        // Draw gradient effect at the end
        if (percentage > 0.05) {
          const gradientAngle = endAngle;
          const gradientX = centerX + radius * Math.cos(gradientAngle);
          const gradientY = centerY + radius * Math.sin(gradientAngle);

          const gradient = ctx.createRadialGradient(
            gradientX, gradientY, 0,
            gradientX, gradientY, strokeWidth * 2
          );
          gradient.addColorStop(0, colors.primary);
          gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

          ctx.beginPath();
          ctx.arc(gradientX, gradientY, strokeWidth * 1.5, 0, Math.PI * 2);
          ctx.fillStyle = gradient;
          ctx.fill();
        }
      }
    }
  }
});
