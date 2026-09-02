#!/command/with-contenv sh
# s6 stage2 hook: pick the optional services for this boot.
#
# Every service the image ships is opt-in via a START_<NAME> environment
# variable; adding it to the user bundle here (before s6-rc computes the boot
# set) is the v3 replacement for the old `down` file that a cont-init script
# deleted. Services the image does not ship are silently skipped, so the worker
# and dns images share this one hook.

enable_service() { # $1 = service name, $2 = value of its START_ variable
    [ "$2" = "YES" ] || return 0
    [ -d "/etc/s6-overlay/s6-rc.d/$1" ] || return 0
    touch "/etc/s6-overlay/user-bundles.d/user/contents.d/$1"
}

enable_service worker "${START_WORKER:-YES}"
enable_service pdns "${START_PDNS:-NO}"
