/** One bounded fetch at a time; superseded sockets and responses cannot repaint. */
export function createLiveStateController({ fetchState, apply, onError = () => {} }) {
  let wanted = null,
    accepted = null,
    running = false,
    active = true,
    generation = 0;
  const valid = stamp =>
    stamp &&
    typeof stamp.epoch === 'string' &&
    stamp.epoch &&
    Number.isSafeInteger(stamp.revision) &&
    stamp.revision > 0;

  async function drain() {
    if (running || !active) return;
    running = true;
    try {
      while (
        active &&
        wanted &&
        (!accepted || accepted.epoch !== wanted.epoch || accepted.revision < wanted.revision)
      ) {
        const requestGeneration = generation;
        const next = await fetchState();
        if (!active) return;
        if (requestGeneration !== generation) continue;
        const stamp = next.live;
        if (!valid(stamp) || stamp.epoch !== wanted.epoch) {
          throw new Error('Live state changed servers; reconnecting.');
        }
        if (stamp.revision < wanted.revision) continue;
        accepted = stamp;
        apply(next);
      }
    } catch (error) {
      if (active) onError(error);
    } finally {
      running = false;
    }
  }

  return {
    notify(message) {
      if (!active || message.type !== 'state_changed' || !valid(message)) return;
      if (wanted && wanted.epoch === message.epoch && message.revision <= wanted.revision) return;
      if (wanted && wanted.epoch !== message.epoch) generation++;
      wanted = { epoch: message.epoch, revision: message.revision };
      void drain();
    },
    dispose() {
      active = false;
      generation++;
    }
  };
}

export function isStaleState(current, next) {
  return !!(
    current?.live &&
    next?.live &&
    current.live.epoch === next.live.epoch &&
    next.live.revision < current.live.revision
  );
}
