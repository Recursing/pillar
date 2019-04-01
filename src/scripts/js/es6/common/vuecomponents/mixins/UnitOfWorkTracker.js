/**
 * Vue helper mixin to keep track if work is in progress or not.
 * Example use:
 *      Keep track of work in own component:
 *          this.unitOfWork(
 *              thenDostuff()
 *                  .then(...)
 *                  .fail(...)
 *          );
 * 
 *      Keep track of work in child components:
 *          <myChild
 *              @unit-of-work="childUnitOfWork"
 *          />
 * 
 *      Use the information to enable class:
 *      <div :class="{disabled: 'isBusyWorking'}">
 */
var UnitOfWorkTracker = {
    data() {
        return {
            unitOfWorkCounter: 0,
        } 
    },
    computed: {
        isBusyWorking() {
            if(this.unitOfWorkCounter < 0) {
                console.error('UnitOfWork missmatch!')
            }
            return this.unitOfWorkCounter > 0;
        }
    },
    watch: {
        isBusyWorking(isBusy) {
            if(isBusy) {
                this.$emit('unit-of-work', 1);
            } else {
                this.$emit('unit-of-work', -1);
            }
        }
    },
    beforeDestroy() {
        if(this.unitOfWorkCounter !== 0) {
            this.$emit('unit-of-work', -this.unitOfWorkCounter);
        }
    },
    methods: {
        unitOfWork(promise) {
            this.unitOfWorkBegin();
            if (promise.always) {
                // jQuery Promise
                return promise.always(this.unitOfWorkDone);
            }
            if (promise.finally) {
                // Native js Promise
                return promise.finally(this.unitOfWorkDone);
            }
            throw Error('Unsupported promise type');
        },
        unitOfWorkBegin() {
            this.unitOfWorkCounter++;
        },
        unitOfWorkDone() {
            this.unitOfWorkCounter--;
        },
        childUnitOfWork(direction) {
            this.unitOfWorkCounter += direction;
        }
    }
}

export { UnitOfWorkTracker }
