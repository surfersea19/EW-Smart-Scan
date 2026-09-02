"""
emitter_behaviors.py

Concrete EmitterBehavior implementations. Each one implements
get_state(t, emitter) and decides, for a given time step, whether the
emitter is active and (for frequency-changing types) what frequency
it's currently on.

All behaviors are driven by simple, explicit rules at this stage —
no randomness dressed up as complexity. Randomization belongs in
scenario_generator.py, which will pick parameters (periods, hop lists,
duty cycles) for these behaviors, not inside the behaviors themselves.
"""

from .emitter import EmitterBehavior, EmitterState


class FixedBehavior(EmitterBehavior):
    """
    Always transmits on the same frequency. May still turn on/off,
    but never changes frequency. This is the simplest possible behavior
    and the baseline every other behavior is compared against.

    Example: on_duration=1, off_duration=0 -> always on (like _AlwaysOnBehavior).
    """

    def __init__(self, on_duration: int = 1, off_duration: int = 0):
        self.on_duration = on_duration
        self.off_duration = off_duration
        self.cycle_length = on_duration + off_duration

    def get_state(self, t: int, emitter) -> EmitterState:
        active = True
        if self.cycle_length > 0:
            phase = t % self.cycle_length
            active = phase < self.on_duration

        return EmitterState(
            time=t,
            emitter_id=emitter.emitter_id,
            active=active,
            frequency_mhz=emitter.center_frequency_mhz if active else None,
            power_db=emitter.power_db if active else None,
            pulse_width_us=emitter.pulse_width_us if active else None,
            pri_us=emitter.pri_us if active else None,
        )


class PeriodicBehavior(EmitterBehavior):
    """
    Transmits in a repeating ON/OFF cycle on a fixed frequency.
    Example: on_duration=3, off_duration=2 -> ON ON ON OFF OFF ON ON ON OFF OFF ...
    This is functionally the general case of FixedBehavior; kept as a
    separate class for clarity/naming, matching the problem statement's
    own vocabulary (section 6).
    """

    def __init__(self, on_duration: int, off_duration: int):
        if on_duration <= 0 or off_duration <= 0:
            raise ValueError("on_duration and off_duration must both be positive")
        self.on_duration = on_duration
        self.off_duration = off_duration
        self.cycle_length = on_duration + off_duration

    def get_state(self, t: int, emitter) -> EmitterState:
        phase = t % self.cycle_length
        active = phase < self.on_duration

        return EmitterState(
            time=t,
            emitter_id=emitter.emitter_id,
            active=active,
            frequency_mhz=emitter.center_frequency_mhz if active else None,
            power_db=emitter.power_db if active else None,
            pulse_width_us=emitter.pulse_width_us if active else None,
            pri_us=emitter.pri_us if active else None,
        )


class BurstyBehavior(EmitterBehavior):
    """
    Transmits at random-ish intervals with a given probability of being
    active at each time step, on a fixed frequency. Unlike PeriodicBehavior,
    there's no fixed cycle — it's intermittent/unpredictable, which is the
    point (models emitters with irregular, non-periodic traffic).

    Uses a seeded RNG so scenarios are reproducible.
    """

    def __init__(self, transmit_probability: float = 0.3, seed: int = None):
        if not (0.0 <= transmit_probability <= 1.0):
            raise ValueError("transmit_probability must be between 0 and 1")
        self.transmit_probability = transmit_probability
        import random
        self._rng = random.Random(seed)
        # Cache decisions per time step so repeated calls for the same t
        # (e.g. from multiple receivers) are consistent.
        self._decisions = {}

    def get_state(self, t: int, emitter) -> EmitterState:
        if t not in self._decisions:
            self._decisions[t] = self._rng.random() < self.transmit_probability
        active = self._decisions[t]

        return EmitterState(
            time=t,
            emitter_id=emitter.emitter_id,
            active=active,
            frequency_mhz=emitter.center_frequency_mhz if active else None,
            power_db=emitter.power_db if active else None,
            pulse_width_us=emitter.pulse_width_us if active else None,
            pri_us=emitter.pri_us if active else None,
        )


class AgileBehavior(EmitterBehavior):
    """
    Frequency-agile: transmits continuously (or on a duty cycle) but
    changes frequency each time it transmits, hopping through a fixed
    list of frequencies (e.g. B40 -> B42 -> B45 -> B41 -> B48).

    This is the classic "hard to catch" emitter — it's always active,
    but a receiver has to guess which of several frequencies it's on
    at any given moment.
    """

    def __init__(self, hop_frequencies_mhz: list, hop_interval: int = 1):
        if not hop_frequencies_mhz:
            raise ValueError("hop_frequencies_mhz must be a non-empty list")
        if hop_interval <= 0:
            raise ValueError("hop_interval must be positive")
        self.hop_frequencies_mhz = hop_frequencies_mhz
        self.hop_interval = hop_interval

    def get_state(self, t: int, emitter) -> EmitterState:
        hop_index = (t // self.hop_interval) % len(self.hop_frequencies_mhz)
        current_freq = self.hop_frequencies_mhz[hop_index]

        return EmitterState(
            time=t,
            emitter_id=emitter.emitter_id,
            active=True,
            frequency_mhz=current_freq,
            power_db=emitter.power_db,
            pulse_width_us=emitter.pulse_width_us,
            pri_us=emitter.pri_us,
        )


class ScanningBehavior(EmitterBehavior):
    """
    Frequency-scanning: sweeps steadily across a frequency range, like
    a receiver would, but as a transmitter. E.g. B10 -> B11 -> ... -> B30,
    optionally reversing direction (ping-pong) instead of wrapping.

    Distinct from AgileBehavior: agile hops to arbitrary listed frequencies
    (can jump anywhere in any order), scanning moves monotonically through
    a contiguous range.
    """

    def __init__(self, freq_start_mhz: float, freq_end_mhz: float,
                 step_mhz: float, step_interval: int = 1, ping_pong: bool = True):
        if freq_end_mhz <= freq_start_mhz:
            raise ValueError("freq_end_mhz must be greater than freq_start_mhz")
        if step_mhz <= 0:
            raise ValueError("step_mhz must be positive")
        self.freq_start_mhz = freq_start_mhz
        self.freq_end_mhz = freq_end_mhz
        self.step_mhz = step_mhz
        self.step_interval = max(1, step_interval)
        self.ping_pong = ping_pong

        span = freq_end_mhz - freq_start_mhz
        self.num_steps = max(1, int(span / step_mhz) + 1)

    def get_state(self, t: int, emitter) -> EmitterState:
        step_count = t // self.step_interval

        if self.ping_pong:
            cycle_len = 2 * (self.num_steps - 1) if self.num_steps > 1 else 1
            phase = step_count % cycle_len if cycle_len > 0 else 0
            index = phase if phase < self.num_steps else cycle_len - phase
        else:
            index = step_count % self.num_steps

        current_freq = min(
            self.freq_start_mhz + index * self.step_mhz,
            self.freq_end_mhz,
        )

        return EmitterState(
            time=t,
            emitter_id=emitter.emitter_id,
            active=True,
            frequency_mhz=current_freq,
            power_db=emitter.power_db,
            pulse_width_us=emitter.pulse_width_us,
            pri_us=emitter.pri_us,
        )


if __name__ == "__main__":
    from .emitter import Emitter, EmitterConfig

    config = EmitterConfig(emitter_id="E1", center_frequency_mhz=6200.0)

    print("--- PeriodicBehavior (on=3, off=2) ---")
    e1 = Emitter(config, PeriodicBehavior(on_duration=3, off_duration=2))
    for t in range(10):
        s = e1.get_state(t)
        print(t, "ACTIVE" if s.active else "off")

    print("\n--- BurstyBehavior (p=0.4, seed=42) ---")
    e2 = Emitter(config, BurstyBehavior(transmit_probability=0.4, seed=42))
    for t in range(10):
        s = e2.get_state(t)
        print(t, "ACTIVE" if s.active else "off")

    print("\n--- AgileBehavior (hop list, interval=2) ---")
    e3 = Emitter(config, AgileBehavior(hop_frequencies_mhz=[6200, 6420, 6650], hop_interval=2))
    for t in range(8):
        s = e3.get_state(t)
        print(t, s.frequency_mhz)

    print("\n--- ScanningBehavior (6000-6500, step=100, ping-pong) ---")
    e4 = Emitter(config, ScanningBehavior(freq_start_mhz=6000, freq_end_mhz=6500, step_mhz=100, step_interval=1))
    for t in range(10):
        s = e4.get_state(t)
        print(t, s.frequency_mhz)
