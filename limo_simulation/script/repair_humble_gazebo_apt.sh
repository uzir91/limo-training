#!/usr/bin/env bash
# Repair APT repository and package-version problems affecting Gazebo Modern
# on Ubuntu 22.04 + ROS 2 Humble.
#
# This script deliberately does NOT:
#   - install ros-humble-* packages
#   - run rosdep
#   - infer dependencies from a workspace
#
# Your package.xml + rosdep remain responsible for ROS dependencies.

set -Eeuo pipefail

SCRIPT_NAME="$(basename "$0")"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="/tmp/${SCRIPT_NAME%.sh}-${TIMESTAMP}.log"
BACKUP_DIR="/var/backups/${SCRIPT_NAME%.sh}-${TIMESTAMP}"
ASSUME_YES=0

usage() {
  cat <<EOF
Usage: $SCRIPT_NAME [--yes]

Repairs Gazebo Modern APT repositories and broken/mismatched Gazebo libraries
for Ubuntu 22.04 Jammy with ROS 2 Humble.

Options:
  -y, --yes   Pass -y to APT operations.
  -h, --help  Show this help.

The repair runs immediately. There is no separate check step.
EOF
}

while (($#)); do
  case "$1" in
    -y|--yes)
      ASSUME_YES=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

exec > >(tee -a "$LOG_FILE") 2>&1

if [[ ${EUID} -eq 0 ]]; then
  SUDO=()
else
  command -v sudo >/dev/null 2>&1 || {
    echo "ERROR: sudo is required when not running as root."
    exit 1
  }
  SUDO=(sudo)
fi

APT_COMMON=(apt-get -o Dpkg::Options::=--force-confold)
if ((ASSUME_YES)); then
  APT_COMMON+=(-y)
fi

info() { printf '\n==> %s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

run_apt() {
  "${SUDO[@]}" "${APT_COMMON[@]}" "$@"
}

require_platform() {
  [[ -r /etc/os-release ]] || die "/etc/os-release is missing."
  # shellcheck disable=SC1091
  source /etc/os-release

  [[ ${ID:-} == "ubuntu" ]] || die "This script supports Ubuntu only; detected '${ID:-unknown}'."
  [[ ${VERSION_CODENAME:-} == "jammy" ]] || \
    die "ROS 2 Humble binary packages expect Ubuntu 22.04 Jammy; detected '${VERSION_CODENAME:-unknown}'."

  local detected_ros="${ROS_DISTRO:-}"
  if [[ -z "$detected_ros" && -d /opt/ros/humble ]]; then
    detected_ros="humble"
  fi

  [[ "$detected_ros" == "humble" ]] || \
    die "ROS 2 Humble was not detected. Source /opt/ros/humble/setup.bash or install Humble first."

  local arch
  arch="$(dpkg --print-architecture)"
  case "$arch" in
    amd64|arm64) ;;
    *) die "Unsupported architecture '$arch'. Expected amd64 or arm64." ;;
  esac

  echo "Ubuntu: ${PRETTY_NAME:-Ubuntu Jammy}"
  echo "ROS distro: humble"
  echo "Gazebo pairing: Fortress library family"
  echo "Architecture: $arch"
}

backup_apt_configuration() {
  info "Backing up APT configuration"
  "${SUDO[@]}" mkdir -p "$BACKUP_DIR"
  "${SUDO[@]}" cp -a /etc/apt/sources.list "$BACKUP_DIR/" 2>/dev/null || true
  "${SUDO[@]}" cp -a /etc/apt/sources.list.d "$BACKUP_DIR/" 2>/dev/null || true
  "${SUDO[@]}" cp -a /etc/apt/preferences "$BACKUP_DIR/" 2>/dev/null || true
  "${SUDO[@]}" cp -a /etc/apt/preferences.d "$BACKUP_DIR/" 2>/dev/null || true
  echo "Backup: $BACKUP_DIR"
}

comment_matching_list_lines() {
  local file="$1"
  local regex="$2"
  local label="$3"
  local tmp

  [[ -f "$file" ]] || return 0
  grep -Eq "^[[:space:]]*deb(-src)?[[:space:]].*${regex}" "$file" || return 0

  tmp="$(mktemp)"
  awk -v regex="$regex" -v label="$label" '
    /^[[:space:]]*deb(-src)?[[:space:]]/ && $0 ~ regex {
      print "# disabled by Gazebo APT repair (" label "): " $0
      next
    }
    { print }
  ' "$file" > "$tmp"

  "${SUDO[@]}" install -m 0644 "$tmp" "$file"
  rm -f "$tmp"
  echo "Updated: $file"
}

remove_matching_deb822_stanzas() {
  local file="$1"
  local regex="$2"
  local label="$3"
  local tmp

  [[ -f "$file" ]] || return 0
  grep -Eqi "$regex" "$file" || return 0

  tmp="$(mktemp)"
  awk -v RS='' -v ORS='\n\n' -v regex="$regex" '
    BEGIN { IGNORECASE=1 }
    $0 !~ regex { print }
  ' "$file" > "$tmp"

  if [[ -s "$tmp" ]]; then
    "${SUDO[@]}" install -m 0644 "$tmp" "$file"
    echo "Removed $label stanza from: $file"
  else
    "${SUDO[@]}" mv "$file" "${file}.disabled-${TIMESTAMP}"
    echo "Disabled file containing only $label: $file"
  fi
  rm -f "$tmp"
}

normalise_repositories() {
  info "Normalising Gazebo and ROS APT channels"

  local file
  shopt -s nullglob

  # Remove every existing OSRF Gazebo line first. A single canonical stable
  # entry is written below, avoiding duplicate, wrong-codename, prerelease,
  # and nightly entries.
  for file in /etc/apt/sources.list /etc/apt/sources.list.d/*.list; do
    comment_matching_list_lines \
      "$file" \
      'packages\.osrfoundation\.org/gazebo/' \
      'replace with canonical ubuntu-stable Jammy entry'

    # ROS testing packages can pull versions ahead of the Humble stable farm
    # and create dependency mismatches. Keep the regular ROS stable source.
    comment_matching_list_lines \
      "$file" \
      'packages\.ros\.org/ros2-testing/' \
      'ROS testing channel conflicts with Humble stable packages'
  done

  for file in /etc/apt/sources.list.d/*.sources; do
    remove_matching_deb822_stanzas \
      "$file" \
      'packages\.osrfoundation\.org/gazebo/' \
      'OSRF Gazebo'

    remove_matching_deb822_stanzas \
      "$file" \
      'packages\.ros\.org/ros2-testing/' \
      'ROS 2 testing'
  done

  shopt -u nullglob

  local keyring="/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg"
  local key_tmp
  key_tmp="$(mktemp)"

  if command -v curl >/dev/null 2>&1; then
    curl --fail --location --silent --show-error \
      https://packages.osrfoundation.org/gazebo.gpg \
      --output "$key_tmp"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$key_tmp" https://packages.osrfoundation.org/gazebo.gpg
  else
    rm -f "$key_tmp"
    die "curl or wget is required to download the OSRF signing key."
  fi

  [[ -s "$key_tmp" ]] || die "Downloaded OSRF key is empty."
  "${SUDO[@]}" install -m 0644 "$key_tmp" "$keyring"
  rm -f "$key_tmp"

  local arch
  arch="$(dpkg --print-architecture)"
  printf '%s\n' \
    "deb [arch=${arch} signed-by=${keyring}] http://packages.osrfoundation.org/gazebo/ubuntu-stable jammy main" \
    | "${SUDO[@]}" tee /etc/apt/sources.list.d/gazebo-stable.list >/dev/null

  echo "Configured: /etc/apt/sources.list.d/gazebo-stable.list"
}

repair_dpkg_and_indexes() {
  info "Repairing dpkg state"
  if ! "${SUDO[@]}" dpkg --configure -a; then
    warn "dpkg configuration is incomplete; continuing with APT dependency repair."
  fi

  info "Refreshing clean APT indexes"
  "${SUDO[@]}" apt-get clean
  "${SUDO[@]}" rm -f \
    /var/lib/apt/lists/*packages.osrfoundation.org* \
    /var/lib/apt/lists/*packages.ros.org_ros2-testing* 2>/dev/null || true
  run_apt update

  info "Repairing broken package dependencies"
  run_apt --fix-broken install
  "${SUDO[@]}" dpkg --configure -a
}

is_held() {
  local wanted="$1"
  apt-mark showhold 2>/dev/null | grep -Fxq "${wanted%%:*}"
}

collect_installed_gazebo_packages() {
  dpkg-query -W -f='${binary:Package}\t${db:Status-Abbrev}\n' 2>/dev/null \
    | awk -F '\t' '$2 ~ /^ii/ {print $1}' \
    | grep -E '^(ignition-|libignition-|gz-|libgz-|sdformat[0-9]|libsdformat|python3-(ignition|gz|sdformat)|ruby-(ignition|gz))' \
    | sort -u || true
}

align_installed_gazebo_versions() {
  info "Checking installed Gazebo Modern library versions"

  mapfile -t packages < <(collect_installed_gazebo_packages)
  if ((${#packages[@]} == 0)); then
    echo "No Gazebo Modern Debian libraries are currently installed."
    echo "Repository repair is complete; rosdep may install required packages later."
    return 0
  fi

  local -a specs=()
  local -a held=()
  local -a orphaned=()
  local pkg installed candidate

  for pkg in "${packages[@]}"; do
    installed="$(dpkg-query -W -f='${Version}' "$pkg" 2>/dev/null || true)"
    candidate="$(apt-cache policy "$pkg" 2>/dev/null | awk '/Candidate:/ {print $2; exit}')"

    if [[ -z "$candidate" || "$candidate" == "(none)" ]]; then
      orphaned+=("$pkg=$installed")
      continue
    fi

    if [[ "$installed" != "$candidate" ]]; then
      if is_held "$pkg"; then
        held+=("$pkg: installed=$installed candidate=$candidate")
      else
        specs+=("$pkg=$candidate")
        printf 'Align: %s  %s -> %s\n' "$pkg" "$installed" "$candidate"
      fi
    fi
  done

  if ((${#specs[@]})); then
    info "Aligning Gazebo libraries with stable repository candidates"
    # --allow-downgrades is necessary after a nightly or prerelease repository
    # has installed a version newer than the stable channel.
    run_apt --allow-downgrades install "${specs[@]}"
    run_apt --fix-broken install
    "${SUDO[@]}" dpkg --configure -a
  else
    echo "Installed Gazebo libraries already match their stable APT candidates."
  fi

  if ((${#held[@]})); then
    warn "Held Gazebo packages were not modified:"
    printf '  %s\n' "${held[@]}"
  fi

  if ((${#orphaned[@]})); then
    warn "Installed Gazebo packages with no APT candidate were left untouched:"
    printf '  %s\n' "${orphaned[@]}"
    warn "These are usually manually installed packages or packages from a removed repository."
  fi
}

report_release_mix() {
  info "Checking for Gazebo release-family conflicts"

  local conflicts=0
  local pkg
  for pkg in \
    ros-humble-ros-gzharmonic \
    gz-garden \
    gz-harmonic \
    gz-ionic \
    gz-jetty; do
    if dpkg-query -W -f='${db:Status-Abbrev}' "$pkg" 2>/dev/null | grep -q '^ii'; then
      warn "$pkg is installed. Humble's normal binary pairing is Gazebo Fortress."
      conflicts=1
    fi
  done

  if ((conflicts)); then
    warn "The script did not remove these packages automatically because that could remove dependent development packages."
    warn "Do not mix ros-humble-ros-gzharmonic with the normal ros-humble-ros-gz package family."
  else
    echo "No conflicting Gazebo distribution meta-package was detected."
  fi
}

final_checks() {
  info "Final APT checks"
  run_apt check

  local audit
  audit="$(dpkg --audit 2>&1 || true)"
  if [[ -n "$audit" ]]; then
    warn "dpkg still reports issues:"
    printf '%s\n' "$audit"
    return 1
  fi

  echo "APT and dpkg report a consistent package state."
}

main() {
  echo "Gazebo Modern APT repair for ROS 2 Humble"
  echo "Log: $LOG_FILE"

  require_platform
  backup_apt_configuration
  normalise_repositories
  repair_dpkg_and_indexes
  align_installed_gazebo_versions
  report_release_mix
  final_checks

  info "Repair complete"
  echo "No ROS dependency package was installed explicitly."
  echo "You can now run rosdep from your workspace using package.xml."
  echo "Log: $LOG_FILE"
  echo "Backup: $BACKUP_DIR"
}

main "$@"
