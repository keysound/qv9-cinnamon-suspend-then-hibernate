#!/usr/bin/python3
"""QV9 Lid Handler v0.8.4-e1: Cinnamon owns sleep; handler assists screen lock."""

import logging
import signal
import sys

from gi.repository import Gio, GLib

VERSION = "0.8.4-e1"

BUS_NAME = "org.freedesktop.login1"
PATH = "/org/freedesktop/login1"
MANAGER = "org.freedesktop.login1.Manager"
PROPS = "org.freedesktop.DBus.Properties"
SCREEN_NAME = "org.cinnamon.ScreenSaver"
SCREEN_PATH = "/org/cinnamon/ScreenSaver"
SCREEN_IFACE = "org.cinnamon.ScreenSaver"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [QV9-LID] %(message)s",
    stream=sys.stdout,
)


class LidHandler:
    def __init__(self):
        self.loop = GLib.MainLoop()
        self.bus = Gio.bus_get_sync(
            Gio.BusType.SYSTEM, None
        )
        self.lid_closed = self.get_property("LidClosed")
        self.sleeping = self.get_property(
            "PreparingForSleep"
        )

        if self.sleeping:
            self.state = "SLEEPING"
        elif self.lid_closed:
            self.state = "WAIT_LID_OPEN"
        else:
            self.state = "READY"

        self.cycle = 0

        try:
            self.screen_bus = Gio.bus_get_sync(
                Gio.BusType.SESSION, None
            )
        except GLib.Error as exc:
            self.screen_bus = None
            logging.warning(
                "Screensaver session bus unavailable: %s", exc
            )

        self.screen_active = self.get_screen_active()
        self.lock_accepted = False
        self.lock_failed = False
        self.lock_ready_logged = False
        self.lock_timer_id = None

    def get_property(self, name):
        result = self.bus.call_sync(
            BUS_NAME, PATH, PROPS, "Get",
            GLib.Variant("(ss)", (MANAGER, name)),
            GLib.VariantType.new("(v)"),
            Gio.DBusCallFlags.NONE,
            5000, None,
        )
        return bool(result.unpack()[0])

    def get_screen_active(self):
        if self.screen_bus is None:
            return None

        try:
            result = self.screen_bus.call_sync(
                SCREEN_NAME, SCREEN_PATH,
                SCREEN_IFACE, "GetActive",
                None,
                GLib.VariantType.new("(b)"),
                Gio.DBusCallFlags.NONE,
                5000, None,
            )
            return bool(result.unpack()[0])
        except GLib.Error as exc:
            logging.warning(
                "Screensaver GetActive failed: %s", exc
            )
            return None

    def screen_status(self, reason):
        active = self.get_screen_active()
        self.screen_active = active

        logging.info(
            "Screensaver status: active=%s (%s)",
            active if active is not None else "unknown",
            reason,
        )

    def on_screen_changed(
        self, bus, sender, path, interface,
        signal_name, parameters, user_data
    ):
        active = bool(parameters.unpack()[0])
        self.screen_active = active
        logging.info(
            "EVENT Screensaver active=%s", active
        )

        if active:
            self.record_lock_ready()

    def cancel_lock_timer(self):
        if self.lock_timer_id is not None:
            GLib.source_remove(self.lock_timer_id)
            self.lock_timer_id = None

    def on_lock_timeout(self, cycle):
        self.lock_timer_id = None

        if cycle != self.cycle:
            return GLib.SOURCE_REMOVE

        if self.state != "LID_CLOSED" or not self.lid_closed:
            return GLib.SOURCE_REMOVE

        if not self.lock_ready_logged:
            self.lock_failed = True
            logging.error(
                "LOCK timeout: cycle=%d; lock state not confirmed",
                cycle
            )

        return GLib.SOURCE_REMOVE

    def on_lock_finished(self, bus, result, cycle):
        try:
            bus.call_finish(result)
        except GLib.Error as exc:
            if cycle == self.cycle and self.lid_closed:
                self.lock_failed = True
                self.cancel_lock_timer()
                logging.error(
                    "LOCK failed: cycle=%d: %s",
                    cycle, exc
                )
            else:
                logging.warning(
                    "LOCK stale error ignored: cycle=%d",
                    cycle
                )
            return

        if (
            cycle != self.cycle
            or self.state != "LID_CLOSED"
            or not self.lid_closed
        ):
            logging.info(
                "LOCK stale reply ignored: cycle=%d current=%d",
                cycle, self.cycle
            )
            return

        if self.lock_failed:
            logging.warning(
                "LOCK late reply ignored: cycle=%d",
                cycle
            )
            return

        self.lock_accepted = True
        logging.info(
            "LOCK request accepted: cycle=%d", cycle
        )
        self.record_lock_ready()

    def request_lock(self):
        cycle = self.cycle

        if self.screen_active is True:
            self.lock_accepted = True
            logging.info(
                "LOCK already active: cycle=%d", cycle
            )
            self.record_lock_ready()
            return

        if self.screen_bus is None:
            self.lock_failed = True
            logging.error(
                "LOCK failed: session bus unavailable"
            )
            return

        logging.info(
            "LOCK requesting Cinnamon Screensaver: cycle=%d",
            cycle
        )

        self.lock_timer_id = GLib.timeout_add(
            5000, self.on_lock_timeout, cycle
        )

        self.screen_bus.call(
            SCREEN_NAME, SCREEN_PATH,
            SCREEN_IFACE, "Lock",
            GLib.Variant("(s)", ("QV9 lid closed",)),
            None,
            Gio.DBusCallFlags.NONE,
            5000, None,
            self.on_lock_finished, cycle,
        )

    def record_lock_ready(self):
        if self.state != "LID_CLOSED":
            return

        if not self.lid_closed or self.sleeping:
            return

        if not self.lock_accepted:
            return

        if self.screen_active is not True:
            return

        if self.lock_ready_logged or self.lock_failed:
            return

        self.lock_ready_logged = True
        self.cancel_lock_timer()

        # Report the verified screen lock once per lid-close cycle.
        # This program never requests suspend or hibernate.
        logging.info(
            "LOCK ready: cycle=%d; Cinnamon owns sleep policy",
            self.cycle,
        )

    def transition(self, new_state, reason):
        if new_state == self.state:
            return

        logging.info(
            "STATE %s -> %s (%s)",
            self.state, new_state, reason
        )
        self.state = new_state

    def on_properties(
        self, bus, sender, path, interface,
        signal_name, parameters, user_data
    ):
        name, changed, invalidated = parameters.unpack()

        if name != MANAGER or "LidClosed" not in changed:
            return

        closed = bool(changed["LidClosed"])

        if closed == self.lid_closed:
            return

        self.lid_closed = closed
        logging.info(
            "EVENT LidClosed=%s", closed
        )

        if closed:
            self.screen_status("lid closed")

        if self.state == "SLEEPING":
            logging.info(
                "Lid changed during sleep cycle; "
                "no new action"
            )
            return

        if not closed:
            self.cancel_lock_timer()
            self.lock_accepted = False
            self.transition("READY", "lid opened")
        elif self.state == "READY":
            self.cycle += 1
            self.cancel_lock_timer()
            self.lock_accepted = False
            self.lock_failed = False
            self.lock_ready_logged = False
            logging.info(
                "CYCLE %d started", self.cycle
            )
            self.transition(
                "LID_CLOSED", "new lid-close event"
            )
            self.request_lock()
        else:
            logging.info(
                "Close event ignored; state=%s",
                self.state
            )

    def on_sleep(
        self, bus, sender, path, interface,
        signal_name, parameters, user_data
    ):
        preparing = bool(parameters.unpack()[0])

        if preparing == self.sleeping:
            return

        self.sleeping = preparing

        if preparing:
            self.cancel_lock_timer()
            self.screen_status("preparing for sleep")
            logging.info("EVENT PrepareForSleep=true")
            self.transition(
                "SLEEPING", "system entering sleep"
            )
        else:
            logging.info("EVENT PrepareForSleep=false")

            if self.lid_closed:
                self.transition(
                    "WAIT_LID_OPEN",
                    "resumed with lid closed"
                )
            else:
                self.transition(
                    "READY",
                    "resumed with lid open"
                )

    def run(self):
        logging.info(
            "QV9 Lid Handler v%s started", VERSION
        )
        logging.info(
            "Initial lid=%s sleeping=%s state=%s",
            "closed" if self.lid_closed else "open",
            self.sleeping,
            self.state,
        )

        self.bus.signal_subscribe(
            BUS_NAME, PROPS, "PropertiesChanged",
            PATH, MANAGER,
            Gio.DBusSignalFlags.NONE,
            self.on_properties, None
        )

        self.bus.signal_subscribe(
            BUS_NAME, MANAGER, "PrepareForSleep",
            PATH, None,
            Gio.DBusSignalFlags.NONE,
            self.on_sleep, None
        )

        if self.screen_bus is not None:
            self.screen_bus.signal_subscribe(
                SCREEN_NAME, SCREEN_IFACE,
                "ActiveChanged", SCREEN_PATH,
                None,
                Gio.DBusSignalFlags.NONE,
                self.on_screen_changed, None,
            )

        self.screen_status("handler startup")
        logging.info("State machine ready")

        logging.info(
            "OBSERVER-ONLY: no lid inhibitor; "
            "no sleep request path; Cinnamon policy unchanged"
        )
        self.loop.run()
        logging.info("Monitor stopped")


def main():
    handler = LidHandler()

    def stop(signum, frame):
        GLib.idle_add(handler.loop.quit)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    handler.run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Fatal handler error")
        sys.exit(1)
