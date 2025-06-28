import os
import sys
from pynput.keyboard import HotKey, Key


class HoldHotKey(HotKey):
    def __init__(self, keys, on_activate, on_deactivate):
        self.active = False
        self._on_activate_callback = on_activate  # Store original callbacks
        self._on_deactivate_callback = on_deactivate

        # Initialize the superclass with our internal activation method
        super().__init__(keys, self._internal_on_activate)

        # Store a reference to our internal deactivate method for use in release()
        self._mod_on_deactivate = self._internal_on_deactivate

    def _internal_on_activate(self):
        """Internal activation logic to prevent re-triggering."""
        if not self.active:
            self.active = True
            self._on_activate_callback()

    def _internal_on_deactivate(self):
        """Internal deactivation logic to prevent unnecessary calls."""
        if self.active:
            self.active = False
            self._on_deactivate_callback()
            # Force reset the internal _state of the HotKey to an empty set.
            # This ensures that all keys are considered "released" by the HotKey
            # object, preventing lingering states that might cause the hotkey
            # to be triggered by single modifier presses later.
            # _state must be a set for pynput's internal operations (e.g., .add())
            self._state = set()


    def press(self, key):
        # Call the original HotKey's press to update its internal state
        super().press(key)

        # If the hotkey combination is fully pressed, activate
        if self._state == self._keys:
            self._internal_on_activate()

    def release(self, key):
        # Call the original HotKey's release to update its internal state
        super().release(key)

        # If the hotkey was active and the internal state no longer matches the full hotkey,
        # it means the hotkey combination is no longer held, so we deactivate.
        if self.active and self._state != self._keys:
            self._internal_on_deactivate()


class HoldGlobeKey:
    """
    For macOS only, globe key requires special handling
    """

    def __init__(self, on_activate, on_deactivate):
        self.held = False
        self._on_activate = on_activate
        self._on_deactivate = on_deactivate

    def press(self, key):
        # Globe key on macOS usually has vk == 63
        if hasattr(key, "vk") and key.vk == 63:
            if self.held:  # If it was held, it's now released (end of hold)
                self._on_deactivate()
            else:  # If it was not held, it's now pressed (start of hold)
                self._on_activate()
            self.held = not self.held # Toggle the held state

    def release(self, key):
        """Press and release signals are mixed for globe key, so we treat release like a press"""
        self.press(key)


def create_keylistener(transcriber, env_var="UTTERTYPE_RECORD_HOTKEYS"):
    key_code = os.getenv(env_var, "")

    if (sys.platform == "darwin") and (key_code in ["<globe>", ""]):
        return HoldGlobeKey(
            on_activate=transcriber.start_recording,
            on_deactivate=transcriber.stop_recording,
        )

    # Default hotkey for Windows/Linux
    key_code = key_code if key_code else "<ctrl>+<alt>+v"

    return HoldHotKey(
        # HotKey.parse converts the string like "<ctrl>+<alt>+v" into a tuple of key objects
        HotKey.parse(key_code),
        on_activate=transcriber.start_recording,
        on_deactivate=transcriber.stop_recording,
    )

