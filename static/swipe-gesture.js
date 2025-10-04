class SwipeGestureController {
    constructor(options = {}) {
        this.thresholds = {
            deadZone: options.deadZone || 16,
            commitThreshold: options.commitThreshold || 0.4,
            velocityMultiplier: options.velocityMultiplier || 1.5,
            verticalTolerance: options.verticalTolerance || 30
        };

        this.state = {
            isActive: false,
            startX: 0,
            startY: 0,
            currentX: 0,
            currentY: 0,
            startTime: 0,
            element: null,
            rowWidth: 0
        };

        this.callbacks = {
            onSwipeLeft: options.onSwipeLeft || null,
            onSwipeRight: options.onSwipeRight || null,
            onSwipeStart: options.onSwipeStart || null,
            onSwipeMove: options.onSwipeMove || null,
            onSwipeEnd: options.onSwipeEnd || null,
            onSwipeCancel: options.onSwipeCancel || null
        };

        this.enabledDirections = {
            left: options.enableLeft !== false,
            right: options.enableRight !== false
        };
    }

    attachToElement(element, selector) {
        const rows = element.querySelectorAll(selector);
        
        rows.forEach(row => {
            row.style.touchAction = 'pan-y';
            row.style.position = 'relative';
            row.style.transition = 'none';
            row.style.cursor = 'grab';

            row.addEventListener('pointerdown', (e) => this.handleStart(e, row), { passive: true });
            row.addEventListener('pointermove', (e) => this.handleMove(e, row));
            row.addEventListener('pointerup', (e) => this.handleEnd(e, row));
            row.addEventListener('pointercancel', (e) => this.handleCancel(e, row));
        });
    }

    handleStart(e, row) {
        if (e.target.closest('button') || e.target.closest('input') || e.target.closest('select')) {
            return;
        }

        this.state.isActive = true;
        this.state.startX = e.clientX;
        this.state.startY = e.clientY;
        this.state.currentX = e.clientX;
        this.state.currentY = e.clientY;
        this.state.startTime = Date.now();
        this.state.element = row;
        this.state.rowWidth = row.offsetWidth;

        row.style.transition = 'none';
        row.style.cursor = 'grabbing';

        if (this.callbacks.onSwipeStart) {
            this.callbacks.onSwipeStart(row);
        }
    }

    handleMove(e, row) {
        if (!this.state.isActive || this.state.element !== row) return;

        this.state.currentX = e.clientX;
        this.state.currentY = e.clientY;

        const deltaX = this.state.currentX - this.state.startX;
        const deltaY = Math.abs(this.state.currentY - this.state.startY);

        if (deltaY > this.thresholds.verticalTolerance && Math.abs(deltaX) < this.thresholds.deadZone) {
            this.cancelSwipe(row);
            return;
        }

        if (Math.abs(deltaX) > this.thresholds.deadZone) {
            e.preventDefault();
            
            const direction = deltaX > 0 ? 'right' : 'left';
            
            if (!this.enabledDirections[direction]) {
                return;
            }

            const maxSwipe = this.state.rowWidth * 0.5;
            const constrainedDelta = Math.max(-maxSwipe, Math.min(maxSwipe, deltaX));

            requestAnimationFrame(() => {
                row.style.transform = `translate3d(${constrainedDelta}px, 0, 0)`;
                
                const progress = Math.abs(constrainedDelta) / (this.state.rowWidth * this.thresholds.commitThreshold);
                const clampedProgress = Math.min(100, progress * 100);
                
                row.setAttribute('data-swipe-progress', Math.floor(clampedProgress));
                row.setAttribute('data-swipe-direction', direction);
                
                if (this.callbacks.onSwipeMove) {
                    this.callbacks.onSwipeMove(row, constrainedDelta, direction, clampedProgress);
                }
            });
        }
    }

    handleEnd(e, row) {
        if (!this.state.isActive || this.state.element !== row) return;

        const deltaX = this.state.currentX - this.state.startX;
        const duration = Date.now() - this.state.startTime;
        const velocity = Math.abs(deltaX) / duration;

        const commitDistance = this.state.rowWidth * this.thresholds.commitThreshold;
        const shouldCommit = Math.abs(deltaX) > commitDistance || velocity > this.thresholds.velocityMultiplier;

        if (shouldCommit && Math.abs(deltaX) > this.thresholds.deadZone) {
            const direction = deltaX > 0 ? 'right' : 'left';
            
            if (this.enabledDirections[direction]) {
                this.commitSwipe(row, direction);
            } else {
                this.cancelSwipe(row);
            }
        } else {
            this.cancelSwipe(row);
        }

        this.state.isActive = false;
        this.state.element = null;
        row.style.cursor = 'grab';
    }

    handleCancel(e, row) {
        if (!this.state.isActive || this.state.element !== row) return;
        this.cancelSwipe(row);
        this.state.isActive = false;
        this.state.element = null;
    }

    commitSwipe(row, direction) {
        row.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        
        const swipeDistance = direction === 'right' ? this.state.rowWidth * 0.4 : -this.state.rowWidth * 0.4;
        row.style.transform = `translate3d(${swipeDistance}px, 0, 0)`;

        if (direction === 'left' && this.callbacks.onSwipeLeft) {
            this.callbacks.onSwipeLeft(row);
        } else if (direction === 'right' && this.callbacks.onSwipeRight) {
            this.callbacks.onSwipeRight(row);
        }

        setTimeout(() => {
            this.resetRow(row);
        }, 300);

        if (this.callbacks.onSwipeEnd) {
            this.callbacks.onSwipeEnd(row, direction);
        }
    }

    cancelSwipe(row) {
        row.style.transition = 'transform 0.2s cubic-bezier(0.4, 0, 0.2, 1)';
        row.style.transform = 'translate3d(0, 0, 0)';
        row.removeAttribute('data-swipe-progress');
        row.removeAttribute('data-swipe-direction');

        if (this.callbacks.onSwipeCancel) {
            this.callbacks.onSwipeCancel(row);
        }
    }

    resetRow(row) {
        row.style.transition = 'transform 0.2s cubic-bezier(0.4, 0, 0.2, 1)';
        row.style.transform = 'translate3d(0, 0, 0)';
        row.removeAttribute('data-swipe-progress');
        row.removeAttribute('data-swipe-direction');
    }

    showUndo(message, onUndo, duration = 5000) {
        const existingToast = document.querySelector('.swipe-undo-toast');
        if (existingToast) {
            existingToast.remove();
        }

        const toast = document.createElement('div');
        toast.className = 'swipe-undo-toast';
        toast.innerHTML = `
            <span class="swipe-undo-message">${message}</span>
            <button class="swipe-undo-btn">UNDO</button>
        `;

        document.body.appendChild(toast);

        const undoBtn = toast.querySelector('.swipe-undo-btn');
        let timeoutId;

        const removeToast = () => {
            toast.classList.add('hiding');
            setTimeout(() => toast.remove(), 300);
            if (timeoutId) clearTimeout(timeoutId);
        };

        undoBtn.addEventListener('click', () => {
            if (onUndo) onUndo();
            removeToast();
        });

        setTimeout(() => {
            toast.classList.add('show');
        }, 10);

        timeoutId = setTimeout(removeToast, duration);

        return removeToast;
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = SwipeGestureController;
}
